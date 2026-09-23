import os
import re
import cv2
import numpy as np
from fuzzywuzzy import fuzz
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


# ============================================================
# EASY OCR — CHARGEMENT LAZY
# ============================================================
# EasyOCR est très lourd et charge PyTorch.
# On évite donc de l'importer au démarrage de Django.
_reader = None


def get_ocr_reader():
    """
    Get or initialize EasyOCR reader.

    EasyOCR is imported only when OCR is actually required.
    This reduces Django startup memory usage on Render.
    """
    global _reader

    if _reader is None:
        try:
            import easyocr

            logger.info("Initializing EasyOCR reader...")

            _reader = easyocr.Reader(
                ['fr', 'en'],
                gpu=False
            )

            logger.info("EasyOCR reader initialized successfully")

        except Exception as e:
            logger.exception(
                "Failed to initialize EasyOCR: %s",
                str(e)
            )
            raise

    return _reader


# ============================================================
# DOCUMENT / FACE VERIFICATION SERVICE
# ============================================================

class DocumentVerificationService:
    """
    Service for intelligent document and face verification.

    Heavy AI libraries such as EasyOCR and DeepFace are
    intentionally loaded lazily to reduce memory consumption
    during Django startup.
    """

    def __init__(self):
        self.ocr_reader = None

    # ========================================================
    # OCR
    # ========================================================

    def _ensure_ocr_reader(self):
        """Ensure OCR reader is initialized."""
        if self.ocr_reader is None:
            self.ocr_reader = get_ocr_reader()

    # ========================================================
    # IMAGE QUALITY
    # ========================================================

    def check_image_quality(self, image_path: str) -> Dict:
        """
        Check image quality for document verification.

        Returns:
            Dictionary containing quality metrics and assessment.
        """
        try:
            img = cv2.imread(image_path)

            if img is None:
                return {
                    'valid': False,
                    'error': 'Unable to read image',
                    'quality_score': 0
                }

            gray = cv2.cvtColor(
                img,
                cv2.COLOR_BGR2GRAY
            )

            # Sharpness
            sharpness = cv2.Laplacian(
                gray,
                cv2.CV_64F
            ).var()

            # Brightness
            brightness = float(np.mean(gray))

            # Contrast
            contrast = float(gray.std())

            # Blur score
            blur_score = sharpness

            quality_score = 0
            issues = []

            # Sharpness
            if sharpness < 50:
                issues.append("Image too blurry")
            else:
                quality_score += 25

            # Brightness
            if brightness < 50:
                issues.append("Image too dark")
            elif brightness > 200:
                issues.append("Image too bright")
            else:
                quality_score += 25

            # Contrast
            if contrast < 30:
                issues.append("Low contrast")
            else:
                quality_score += 25

            # Blur
            if blur_score < 50:
                issues.append("Image appears blurry")
            else:
                quality_score += 25

            return {
                'valid': quality_score >= 50,
                'quality_score': quality_score,
                'sharpness': sharpness,
                'brightness': brightness,
                'contrast': contrast,
                'blur_score': blur_score,
                'issues': issues,
                'message': (
                    'Good quality'
                    if quality_score >= 50
                    else f'Poor quality: {", ".join(issues)}'
                )
            }

        except Exception as e:
            logger.exception(
                "Error checking image quality: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e),
                'quality_score': 0
            }

    # ========================================================
    # OCR TEXT EXTRACTION
    # ========================================================

    def extract_text_from_image(
        self,
        image_path: str
    ) -> List[str]:
        """
        Extract text from image using EasyOCR.

        EasyOCR is loaded only when this method is called.
        """
        try:
            self._ensure_ocr_reader()

            results = self.ocr_reader.readtext(
                image_path
            )

            texts = [
                text[1]
                for text in results
                if len(text) >= 3 and text[2] > 0.5
            ]

            return texts

        except Exception as e:
            logger.exception(
                "Error extracting text: %s",
                str(e)
            )
            return []

    # ========================================================
    # CNI VERIFICATION
    # ========================================================

    def verify_cni_document(
        self,
        image_path: str,
        expected_name: Optional[str] = None
    ) -> Dict:
        """
        Verify CNI document and extract information.
        """
        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': 'Image quality too poor for verification',
                    'quality_check': quality_check
                }

            texts = self.extract_text_from_image(
                image_path
            )

            if not texts:
                return {
                    'valid': False,
                    'error': 'No text could be extracted from document',
                    'quality_check': quality_check
                }

            full_text = ' '.join(texts).upper()

            extracted_info = {
                'name': self._extract_name(full_text),
                'first_name': self._extract_first_name(full_text),
                'birth_date': self._extract_birth_date(full_text),
                'id_number': self._extract_id_number(full_text),
                'place_of_birth': self._extract_place_of_birth(full_text),
                'sex': self._extract_sex(full_text),
                'expiry_date': self._extract_expiry_date(full_text),
                'raw_text': texts,
                'full_text': full_text
            }

            name_match = None

            if expected_name:
                name_match = self._verify_name_match(
                    expected_name,
                    extracted_info
                )

            is_cni = self._is_likely_cni(
                full_text
            )

            return {
                'valid': (
                    is_cni
                    and (
                        name_match is None
                        or name_match['match']
                    )
                ),
                'is_cni': is_cni,
                'extracted_info': extracted_info,
                'name_match': name_match,
                'quality_check': quality_check,
                'confidence': self._calculate_cni_confidence(
                    extracted_info,
                    is_cni
                )
            }

        except Exception as e:
            logger.exception(
                "Error verifying CNI: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    # ========================================================
    # CNI DATA EXTRACTION
    # ========================================================

    def _extract_name(
        self,
        text: str
    ) -> Optional[str]:
        """Extract surname from CNI text."""

        patterns = [
            r'NOM\s*[:\s]+([A-Z\s]+)',
            r'NAME\s*[:\s]+([A-Z\s]+)',
            r'SURNAME\s*[:\s]+([A-Z\s]+)',
            r'FAMILLE\s*[:\s]+([A-Z\s]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                name = match.group(1).strip()

                if len(name) > 2:
                    return name

        return None

    def _extract_first_name(
        self,
        text: str
    ) -> Optional[str]:
        """Extract first name from CNI text."""

        patterns = [
            r'PRÉNOM\s*[:\s]+([A-Z\s]+)',
            r'PRENOM\s*[:\s]+([A-Z\s]+)',
            r'FIRST\s*NAME\s*[:\s]+([A-Z\s]+)',
            r'GIVEN\s*NAME\s*[:\s]+([A-Z\s]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                name = match.group(1).strip()

                if len(name) > 2:
                    return name

        return None

    def _extract_birth_date(
        self,
        text: str
    ) -> Optional[str]:
        """Extract birth date from CNI text."""

        patterns = [
            r'NÉ\s*LE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'NE\s*LE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'NÉE\s*LE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'NEE\s*LE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'DATE\s*DE\s*NAISSANCE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'BORN\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'DOB\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                return match.group(1)

        return None

    def _extract_id_number(
        self,
        text: str
    ) -> Optional[str]:
        """Extract ID number from CNI text."""

        patterns = [
            r'N°\s*([A-Z0-9]+)',
            r'NUMÉRO\s*[:\s]+([A-Z0-9]+)',
            r'NUMERO\s*[:\s]+([A-Z0-9]+)',
            r'ID\s*[:\s]+([A-Z0-9]+)',
            r'CNI\s*[:\s]+([A-Z0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                num = match.group(1).strip()

                if len(num) > 5:
                    return num

        return None

    def _extract_place_of_birth(
        self,
        text: str
    ) -> Optional[str]:
        """Extract place of birth from CNI text."""

        patterns = [
            r'À\s*[:\s]+([A-Z\s]+)',
            r'A\s*[:\s]+([A-Z\s]+)',
            r'PLACE\s*OF\s*BIRTH\s*[:\s]+([A-Z\s]+)',
            r'LIEU\s*DE\s*NAISSANCE\s*[:\s]+([A-Z\s]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                place = match.group(1).strip()

                if len(place) > 2:
                    return place

        return None

    def _extract_sex(
        self,
        text: str
    ) -> Optional[str]:
        """Extract sex from CNI text."""

        if (
            'MASCULIN' in text
            or ('M' in text and 'FÉMININ' not in text)
        ):
            return 'M'

        if (
            'FÉMININ' in text
            or ('F' in text and 'MASCULIN' not in text)
        ):
            return 'F'

        if 'MALE' in text:
            return 'M'

        if 'FEMALE' in text:
            return 'F'

        return None

    def _extract_expiry_date(
        self,
        text: str
    ) -> Optional[str]:
        """Extract expiry date from CNI text."""

        patterns = [
            r'VALABLE\s*JUSQU\'AU\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'EXPIRY\s*DATE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'EXPIRATION\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'DATE\s*D\'EXPIRATION\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                return match.group(1)

        return None

    # ========================================================
    # NAME COMPARISON
    # ========================================================

    def _verify_name_match(
        self,
        expected_name: str,
        extracted_info: Dict
    ) -> Dict:
        """Verify if expected name matches extracted information."""

        expected_upper = (
            expected_name
            .upper()
            .strip()
        )

        extracted_name = extracted_info.get('name')
        extracted_first_name = extracted_info.get('first_name')

        matches = []
        scores = []

        if extracted_name:
            score = fuzz.ratio(
                expected_upper,
                extracted_name
            )

            scores.append(score)

            matches.append({
                'field': 'name',
                'expected': expected_upper,
                'extracted': extracted_name,
                'score': score,
                'match': score > 70
            })

        if extracted_first_name:
            score = fuzz.ratio(
                expected_upper,
                extracted_first_name
            )

            scores.append(score)

            matches.append({
                'field': 'first_name',
                'expected': expected_upper,
                'extracted': extracted_first_name,
                'score': score,
                'match': score > 70
            })

        if extracted_name and extracted_first_name:
            combined = (
                f"{extracted_name} "
                f"{extracted_first_name}"
            )

            score = fuzz.ratio(
                expected_upper,
                combined
            )

            scores.append(score)

            matches.append({
                'field': 'combined',
                'expected': expected_upper,
                'extracted': combined,
                'score': score,
                'match': score > 70
            })

        avg_score = (
            sum(scores) / len(scores)
            if scores
            else 0
        )

        return {
            'match': avg_score > 70,
            'average_score': avg_score,
            'matches': matches
        }

    # ========================================================
    # CNI DETECTION
    # ========================================================

    def _is_likely_cni(
        self,
        text: str
    ) -> bool:
        """Check if document appears to be a CNI."""

        cni_keywords = [
            'CARTE',
            'IDENTITÉ',
            'IDENTITE',
            'NATIONALE',
            'CNI',
            'RÉPUBLIQUE',
            'DU',
            'CAMEROUN',
            'CAMEROON',
            'PRÉNOM',
            'PRENOM',
            'NOM',
            'NÉ',
            'NE',
            'NÉE',
            'NEE',
            'DATE',
            'NAISSANCE',
            'LIEU',
            'SEXE',
            'SIGNATURE',
            'IDENTITY',
            'CARD',
            'NATIONAL',
            'BIRTH',
            'PLACE'
        ]

        text_upper = text.upper()

        keyword_count = sum(
            1
            for keyword in cni_keywords
            if keyword in text_upper
        )

        return keyword_count >= 3

    def _calculate_cni_confidence(
        self,
        extracted_info: Dict,
        is_cni: bool
    ) -> float:
        """Calculate confidence score for CNI verification."""

        if not is_cni:
            return 0.0

        score = 0.0
        max_score = 6.0

        if extracted_info.get('name'):
            score += 1.0

        if extracted_info.get('first_name'):
            score += 1.0

        if extracted_info.get('birth_date'):
            score += 1.0

        if extracted_info.get('id_number'):
            score += 1.0

        if extracted_info.get('place_of_birth'):
            score += 1.0

        if extracted_info.get('sex'):
            score += 1.0

        return (score / max_score) * 100

    # ========================================================
    # LICENSE PLATE DETECTION
    # ========================================================

    def detect_license_plate(
        self,
        image_path: str,
        expected_plate: Optional[str] = None
    ) -> Dict:
        """
        Detect and read license plate from vehicle image.
        """

        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': 'Image quality too poor for plate detection',
                    'quality_check': quality_check
                }

            img = cv2.imread(image_path)

            if img is None:
                return {
                    'valid': False,
                    'error': 'Unable to read image',
                    'quality_check': quality_check
                }

            gray = cv2.cvtColor(
                img,
                cv2.COLOR_BGR2GRAY
            )

            bilateral = cv2.bilateralFilter(
                gray,
                11,
                15,
                15
            )

            edged = cv2.Canny(
                bilateral,
                30,
                200
            )

            contours, _ = cv2.findContours(
                edged.copy(),
                cv2.RETR_TREE,
                cv2.CHAIN_APPROX_SIMPLE
            )

            contours = sorted(
                contours,
                key=cv2.contourArea,
                reverse=True
            )[:10]

            plate_region = None

            for contour in contours:
                approx = cv2.approxPolyDP(
                    contour,
                    0.018 * cv2.arcLength(
                        contour,
                        True
                    ),
                    True
                )

                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(
                        approx
                    )

                    if h == 0:
                        continue

                    aspect_ratio = w / float(h)

                    if (
                        2.0 <= aspect_ratio <= 5.0
                        and w > 50
                        and h > 20
                    ):
                        plate_region = gray[
                            y:y + h,
                            x:x + w
                        ]
                        break

            if plate_region is None:
                plate_region = gray

            self._ensure_ocr_reader()

            results = self.ocr_reader.readtext(
                plate_region
            )

            plate_numbers = []

            for result in results:
                if len(result) < 3:
                    continue

                _, text, confidence = result

                if confidence > 0.6:
                    cleaned_text = (
                        text
                        .upper()
                        .replace(' ', '')
                        .replace('-', '')
                    )

                    if re.match(
                        r'^[A-Z0-9]{2,12}$',
                        cleaned_text
                    ):
                        plate_numbers.append({
                            'text': cleaned_text,
                            'confidence': float(confidence)
                        })

            if not plate_numbers:
                return {
                    'valid': False,
                    'error': 'No license plate detected',
                    'quality_check': quality_check,
                    'detected_plates': []
                }

            best_plate = max(
                plate_numbers,
                key=lambda x: x['confidence']
            )

            plate_match = None

            if expected_plate:
                plate_match = self._verify_plate_match(
                    expected_plate,
                    best_plate['text']
                )

            return {
                'valid': (
                    plate_match is None
                    or plate_match['match']
                ),
                'detected_plate': best_plate['text'],
                'confidence': best_plate['confidence'],
                'all_detected_plates': plate_numbers,
                'plate_match': plate_match,
                'quality_check': quality_check
            }

        except Exception as e:
            logger.exception(
                "Error detecting license plate: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    def _verify_plate_match(
        self,
        expected_plate: str,
        detected_plate: str
    ) -> Dict:
        """Verify if detected plate matches expected plate."""

        expected_upper = (
            expected_plate
            .upper()
            .replace(' ', '')
            .replace('-', '')
        )

        detected_upper = (
            detected_plate
            .upper()
            .replace(' ', '')
            .replace('-', '')
        )

        score = fuzz.ratio(
            expected_upper,
            detected_upper
        )

        return {
            'match': score > 80,
            'score': score,
            'expected': expected_upper,
            'detected': detected_upper
        }

    # ========================================================
    # VEHICLE DOCUMENT
    # ========================================================

    def verify_vehicle_document(
        self,
        image_path: str,
        expected_plate: Optional[str] = None
    ) -> Dict:
        """
        Verify vehicle registration document.
        """

        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': 'Image quality too poor for verification',
                    'quality_check': quality_check
                }

            texts = self.extract_text_from_image(
                image_path
            )

            if not texts:
                return {
                    'valid': False,
                    'error': 'No text could be extracted from document',
                    'quality_check': quality_check
                }

            full_text = ' '.join(texts).upper()

            extracted_info = {
                'plate_number': self._extract_plate_from_document(
                    full_text
                ),
                'vehicle_type': self._extract_vehicle_type(
                    full_text
                ),
                'owner_name': self._extract_owner_name(
                    full_text
                ),
                'registration_date': self._extract_registration_date(
                    full_text
                ),
                'raw_text': texts,
                'full_text': full_text
            }

            plate_match = None

            if (
                expected_plate
                and extracted_info['plate_number']
            ):
                plate_match = self._verify_plate_match(
                    expected_plate,
                    extracted_info['plate_number']
                )

            is_vehicle_doc = (
                self._is_likely_vehicle_document(
                    full_text
                )
            )

            return {
                'valid': (
                    is_vehicle_doc
                    and (
                        plate_match is None
                        or plate_match['match']
                    )
                ),
                'is_vehicle_document': is_vehicle_doc,
                'extracted_info': extracted_info,
                'plate_match': plate_match,
                'quality_check': quality_check,
                'confidence': self._calculate_vehicle_doc_confidence(
                    extracted_info,
                    is_vehicle_doc
                )
            }

        except Exception as e:
            logger.exception(
                "Error verifying vehicle document: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    def _extract_plate_from_document(
        self,
        text: str
    ) -> Optional[str]:
        """Extract license plate from vehicle document."""

        patterns = [
            r'IMMATRICULATION\s*[:\s]+([A-Z0-9]+)',
            r'PLAQUE\s*[:\s]+([A-Z0-9]+)',
            r'NUMÉRO\s*DE\s*PLAQUE\s*[:\s]+([A-Z0-9]+)',
            r'REGISTRATION\s*[:\s]+([A-Z0-9]+)',
            r'N°\s*IMMAT\s*[:\s]+([A-Z0-9]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                plate = match.group(1).strip()

                if len(plate) >= 5:
                    return plate

        return None

    def _extract_vehicle_type(
        self,
        text: str
    ) -> Optional[str]:
        """Extract vehicle type from document."""

        patterns = [
            r'TYPE\s*DE\s*VÉHICULE\s*[:\s]+([A-Z0-9\s]+)',
            r'TYPE\s*VEHICULE\s*[:\s]+([A-Z0-9\s]+)',
            r'VEHICLE\s*TYPE\s*[:\s]+([A-Z0-9\s]+)',
            r'CARROSSERIE\s*[:\s]+([A-Z0-9\s]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                return match.group(1).strip()

        return None

    def _extract_owner_name(
        self,
        text: str
    ) -> Optional[str]:
        """Extract owner name from vehicle document."""

        patterns = [
            r'NOM\s*DU\s*PROPRIÉTAIRE\s*[:\s]+([A-Z\s]+)',
            r'PROPRIÉTAIRE\s*[:\s]+([A-Z\s]+)',
            r'OWNER\s*[:\s]+([A-Z\s]+)',
            r'TITULAIRE\s*[:\s]+([A-Z\s]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                return match.group(1).strip()

        return None

    def _extract_registration_date(
        self,
        text: str
    ) -> Optional[str]:
        """Extract registration date from document."""

        patterns = [
            r'DATE\s*DE\s*PREMIÈRE\s*IMMAT\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'DATE\s*D\'IMMATRICULATION\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})',
            r'REGISTRATION\s*DATE\s*[:\s]+(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                return match.group(1)

        return None

    def _is_likely_vehicle_document(
        self,
        text: str
    ) -> bool:
        """Check if document appears to be vehicle registration."""

        vehicle_keywords = [
            'CARTE',
            'GRISE',
            'IMMATRICULATION',
            'PLAQUE',
            'VÉHICULE',
            'VEHICULE',
            'PROPRIÉTAIRE',
            'PROPRIETAIRE',
            'REGISTRATION',
            'CERTIFICATE',
            'OWNERSHIP',
            'RÉPUBLIQUE',
            'DU',
            'CAMEROUN'
        ]

        text_upper = text.upper()

        keyword_count = sum(
            1
            for keyword in vehicle_keywords
            if keyword in text_upper
        )

        return keyword_count >= 2

    def _calculate_vehicle_doc_confidence(
        self,
        extracted_info: Dict,
        is_vehicle_doc: bool
    ) -> float:
        """Calculate confidence score for vehicle document."""

        if not is_vehicle_doc:
            return 0.0

        score = 0.0
        max_score = 4.0

        if extracted_info.get('plate_number'):
            score += 1.0

        if extracted_info.get('vehicle_type'):
            score += 1.0

        if extracted_info.get('owner_name'):
            score += 1.0

        if extracted_info.get('registration_date'):
            score += 1.0

        return (score / max_score) * 100

    # ========================================================
    # FACE DETECTION — OPENCV
    # ========================================================

    def detect_face(
        self,
        image_path: str
    ) -> Dict:
        """
        Detect face in profile photo using OpenCV Haar Cascade.
        """

        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': 'Image quality too poor for face detection',
                    'quality_check': quality_check
                }

            img = cv2.imread(image_path)

            if img is None:
                return {
                    'valid': False,
                    'error': 'Unable to read image',
                    'quality_check': quality_check
                }

            gray = cv2.cvtColor(
                img,
                cv2.COLOR_BGR2GRAY
            )

            try:
                face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades
                    + 'haarcascade_frontalface_default.xml'
                )

                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )

                face_detected = len(faces) > 0

                if face_detected:
                    largest_face = max(
                        faces,
                        key=lambda x: x[2] * x[3]
                    )

                    x, y, w, h = largest_face

                    img_height, img_width = img.shape[:2]

                    face_area = w * h
                    img_area = img_width * img_height

                    face_ratio = (
                        face_area / img_area
                        if img_area > 0
                        else 0
                    )

                    face_center_x = x + w / 2
                    face_center_y = y + h / 2

                    img_center_x = img_width / 2
                    img_center_y = img_height / 2

                    distance_from_center = (
                        (
                            (face_center_x - img_center_x) ** 2
                        )
                        + (
                            (face_center_y - img_center_y) ** 2
                        )
                    ) ** 0.5

                    max_distance = (
                        min(img_width, img_height) / 4
                    )

                    is_well_centered = (
                        distance_from_center < max_distance
                    )

                    is_well_sized = (
                        0.1 < face_ratio < 0.5
                    )

                    return {
                        'valid': (
                            is_well_centered
                            and is_well_sized
                        ),
                        'face_detected': True,
                        'face_count': len(faces),
                        'face_position': {
                            'x': int(x),
                            'y': int(y),
                            'width': int(w),
                            'height': int(h)
                        },
                        'face_ratio': face_ratio,
                        'is_well_centered': is_well_centered,
                        'is_well_sized': is_well_sized,
                        'quality_check': quality_check,
                        'message': (
                            'Face detected and well-positioned'
                            if (
                                is_well_centered
                                and is_well_sized
                            )
                            else
                            'Face detected but needs better positioning'
                        )
                    }

                return {
                    'valid': False,
                    'face_detected': False,
                    'face_count': 0,
                    'quality_check': quality_check,
                    'message': 'No face detected in the image'
                }

            except Exception as e:
                logger.exception(
                    "Error in face detection: %s",
                    str(e)
                )

                return {
                    'valid': False,
                    'error': f'Face detection failed: {str(e)}',
                    'quality_check': quality_check
                }

        except Exception as e:
            logger.exception(
                "Error detecting face: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    # ========================================================
    # DEEPFACE — FACE EMBEDDING
    # ========================================================

    def generate_face_embedding(
        self,
        image_path: str
    ) -> Dict:
        """
        Generate face embedding using DeepFace.

        DeepFace is imported lazily to prevent high memory
        usage during Django startup.
        """

        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': 'Image quality too poor for face recognition',
                    'quality_check': quality_check
                }

            try:
                # IMPORTANT:
                # Import DeepFace only when needed.
                from deepface import DeepFace

                logger.info(
                    "DeepFace loaded. Generating face embedding..."
                )

                embeddings = DeepFace.represent(
                    img_path=image_path,
                    model_name='VGG-Face',
                    enforce_detection=False
                )

                if embeddings and len(embeddings) > 0:
                    embedding = embeddings[0]

                    embedding_vector = embedding[
                        'embedding'
                    ]

                    facial_area = embedding.get(
                        'facial_area',
                        {}
                    )

                    return {
                        'valid': True,
                        'embedding': embedding_vector,
                        'facial_area': facial_area,
                        'face_count': len(embeddings),
                        'quality_check': quality_check,
                        'message': (
                            'Face embedding generated successfully'
                        )
                    }

                return {
                    'valid': False,
                    'error': 'No face detected in the image',
                    'quality_check': quality_check
                }

            except Exception as e:
                logger.exception(
                    "Error generating face embedding: %s",
                    str(e)
                )

                return {
                    'valid': False,
                    'error': (
                        'Face embedding generation failed: '
                        f'{str(e)}'
                    ),
                    'quality_check': quality_check
                }

        except Exception as e:
            logger.exception(
                "Error in face embedding generation: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    # ========================================================
    # DEEPFACE — FACE VERIFICATION
    # ========================================================

    def verify_face_match(
        self,
        image1_path: str,
        image2_path: str,
        threshold: float = 0.4
    ) -> Dict:
        """
        Verify if two face images match using DeepFace.

        DeepFace is imported lazily.
        """

        try:
            quality1 = self.check_image_quality(
                image1_path
            )

            quality2 = self.check_image_quality(
                image2_path
            )

            if (
                not quality1['valid']
                or not quality2['valid']
            ):
                return {
                    'valid': False,
                    'error': (
                        'Image quality too poor '
                        'for face verification'
                    ),
                    'quality_check_1': quality1,
                    'quality_check_2': quality2
                }

            try:
                # IMPORTANT:
                # Import DeepFace only when needed.
                from deepface import DeepFace

                logger.info(
                    "DeepFace loaded. Verifying face match..."
                )

                result = DeepFace.verify(
                    img1_path=image1_path,
                    img2_path=image2_path,
                    model_name='VGG-Face',
                    enforce_detection=False
                )

                verified = result.get(
                    'verified',
                    False
                )

                distance = result.get(
                    'distance',
                    1.0
                )

                threshold_used = result.get(
                    'threshold',
                    threshold
                )

                return {
                    'valid': verified,
                    'verified': verified,
                    'distance': distance,
                    'threshold': threshold_used,
                    'similarity': 1.0 - distance,
                    'quality_check_1': quality1,
                    'quality_check_2': quality2,
                    'message': (
                        'Faces match'
                        if verified
                        else 'Faces do not match'
                    )
                }

            except Exception as e:
                logger.exception(
                    "Error verifying face match: %s",
                    str(e)
                )

                return {
                    'valid': False,
                    'error': (
                        'Face verification failed: '
                        f'{str(e)}'
                    ),
                    'quality_check_1': quality1,
                    'quality_check_2': quality2
                }

        except Exception as e:
            logger.exception(
                "Error in face verification: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    # ========================================================
    # FACE VERIFICATION WITH STORED EMBEDDING
    # ========================================================

    def verify_face_with_embedding(
        self,
        image_path: str,
        stored_embedding: List[float],
        threshold: float = 0.4
    ) -> Dict:
        """
        Verify if a face image matches a stored embedding.
        """

        try:
            quality_check = self.check_image_quality(
                image_path
            )

            if not quality_check['valid']:
                return {
                    'valid': False,
                    'error': (
                        'Image quality too poor '
                        'for face verification'
                    ),
                    'quality_check': quality_check
                }

            embedding_result = (
                self.generate_face_embedding(
                    image_path
                )
            )

            if not embedding_result['valid']:
                return embedding_result

            new_embedding = embedding_result[
                'embedding'
            ]

            # Import SciPy only when this operation is used.
            from scipy.spatial.distance import cosine

            distance = cosine(
                stored_embedding,
                new_embedding
            )

            similarity = 1.0 - distance

            verified = (
                similarity >= (1.0 - threshold)
            )

            return {
                'valid': verified,
                'verified': verified,
                'distance': distance,
                'similarity': similarity,
                'threshold': threshold,
                'quality_check': quality_check,
                'message': (
                    'Face matches stored embedding'
                    if verified
                    else
                    'Face does not match stored embedding'
                )
            }

        except Exception as e:
            logger.exception(
                "Error verifying face with embedding: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }

    # ========================================================
    # DOCUMENT COMPARISON
    # ========================================================

    def compare_documents(
        self,
        doc1_path: str,
        doc2_path: str
    ) -> Dict:
        """
        Compare two documents for data consistency.
        """

        try:
            text1 = self.extract_text_from_image(
                doc1_path
            )

            text2 = self.extract_text_from_image(
                doc2_path
            )

            if not text1 or not text2:
                return {
                    'valid': False,
                    'error': (
                        'Could not extract text from '
                        'one or both documents'
                    )
                }

            full_text1 = ' '.join(text1)
            full_text2 = ' '.join(text2)

            similarity = fuzz.ratio(
                full_text1,
                full_text2
            )

            name1 = self._extract_name(
                full_text1.upper()
            )

            name2 = self._extract_name(
                full_text2.upper()
            )

            field_comparisons = []

            if name1 and name2:
                name_score = fuzz.ratio(
                    name1,
                    name2
                )

                field_comparisons.append({
                    'field': 'name',
                    'doc1': name1,
                    'doc2': name2,
                    'score': name_score,
                    'match': name_score > 70
                })

            return {
                'valid': True,
                'overall_similarity': similarity,
                'field_comparisons': field_comparisons,
                'documents_match': similarity > 50
            }

        except Exception as e:
            logger.exception(
                "Error comparing documents: %s",
                str(e)
            )

            return {
                'valid': False,
                'error': str(e)
            }


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_verification_service = None


def get_verification_service():
    """
    Get or create verification service instance.
    """

    global _verification_service

    if _verification_service is None:
        _verification_service = (
            DocumentVerificationService()
        )

    return _verification_service

