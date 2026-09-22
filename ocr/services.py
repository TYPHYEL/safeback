import boto3
import os
from django.conf import settings
from PIL import Image
import re
from datetime import datetime

class OCRService:
    """Service for OCR text extraction using AWS Textract"""
    
    def __init__(self):
        self.textract_client = boto3.client(
            'textract',
            region_name=getattr(settings, 'AWS_REGION', 'us-east-1'),
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        )
    
    def extract_text_from_image(self, image_path):
        """Extract text from an image file using AWS Textract"""
        try:
            with open(image_path, 'rb') as image_file:
                response = self.textract_client.detect_document_text(
                    Document={'Bytes': image_file.read()}
                )
            
            # Extract all text blocks
            text_blocks = []
            if 'Blocks' in response and response['Blocks']:
                for block in response['Blocks']:
                    if block.get('BlockType') == 'LINE' and 'Text' in block:
                        text_blocks.append(block['Text'])
            
            return ' '.join(text_blocks) if text_blocks else ''
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ''
    
    def parse_cni_info(self, text):
        """Parse CNI information from extracted text"""
        info = {
            'name': None,
            'first_name': None,
            'birth_date': None,
            'sex': None,
            'confidence': 0.0
        }
        
        if not text:
            return info
        
        text_upper = text.upper()
        
        # Try to extract name patterns (Cameroon CNI format)
        # Common patterns: "NOM:", "PRENOM:", "NE(E) LE:", "SEXE:"
        name_match = re.search(r'NOM\s*[:\s]+([A-Z\s]+)', text_upper)
        if name_match:
            info['name'] = name_match.group(1).strip()
            info['confidence'] += 0.3
        
        first_name_match = re.search(r'PRENOM\s*[:\s]+([A-Z\s]+)', text_upper)
        if first_name_match:
            info['first_name'] = first_name_match.group(1).strip()
            info['confidence'] += 0.3
        
        # Date of birth patterns
        date_patterns = [
            r'NE\(E\)\s*LE\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            r'NE\s*LE\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            r'NÉE?\s*LE\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})'  # Generic date pattern
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text_upper)
            if date_match:
                info['birth_date'] = date_match.group(1)
                info['confidence'] += 0.2
                break
        
        # Sex patterns
        sex_match = re.search(r'SEXE\s*[:\s]+([MF])', text_upper)
        if sex_match:
            info['sex'] = sex_match.group(1)
            info['confidence'] += 0.2
        
        return info
    
    def parse_license_info(self, text):
        """Parse driver license information from extracted text"""
        info = {
            'name': None,
            'first_name': None,
            'birth_date': None,
            'sex': None,
            'license_number': None,
            'confidence': 0.0
        }
        
        if not text:
            return info
        
        text_upper = text.upper()
        
        # Cameroon driver license patterns
        name_match = re.search(r'NOM\s*[:\s]+([A-Z\s]+)', text_upper)
        if name_match:
            info['name'] = name_match.group(1).strip()
            info['confidence'] += 0.25
        
        first_name_match = re.search(r'PRENOM\s*[:\s]+([A-Z\s]+)', text_upper)
        if first_name_match:
            info['first_name'] = first_name_match.group(1).strip()
            info['confidence'] += 0.25
        
        # License number pattern
        license_match = re.search(r'N°\s*[:\s]+([A-Z0-9]+)', text_upper)
        if license_match:
            info['license_number'] = license_match.group(1)
            info['confidence'] += 0.25
        
        # Date patterns
        date_patterns = [
            r'NE\(E\)\s*LE\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            r'NÉE?\s*LE\s*[:\s]+(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text_upper)
            if date_match:
                info['birth_date'] = date_match.group(1)
                info['confidence'] += 0.15
                break
        
        # Sex patterns
        sex_match = re.search(r'SEXE\s*[:\s]+([MF])', text_upper)
        if sex_match:
            info['sex'] = sex_match.group(1)
            info['confidence'] += 0.1
        
        return info
    
    def detect_license_plate(self, text):
        """Detect license plate number from vehicle photo text"""
        if not text:
            return None, 0.0
        
        text_upper = text.upper()
        
        # Cameroon license plate patterns: LT 123 AB, 123 AB 123, etc.
        plate_patterns = [
            r'[A-Z]{2}\s*\d{3,4}\s*[A-Z]{2}',  # LT 123 AB
            r'\d{3,4}\s*[A-Z]{2}\s*\d{3,4}',    # 123 AB 123
            r'[A-Z]{2}\s*\d{3,4}',               # LT 123
            r'\d{3,4}\s*[A-Z]{2}',               # 123 AB
        ]
        
        for pattern in plate_patterns:
            match = re.search(pattern, text_upper)
            if match:
                plate = match.group(0).replace(' ', '')
                return plate, 0.7  # Moderate confidence for plate detection
        
        return None, 0.0
    
    def compare_documents(self, cni_info, license_info, user_info):
        """Compare information between CNI and license"""
        comparison = {
            'name_match': False,
            'first_name_match': False,
            'birth_date_match': False,
            'sex_match': False,
            'overall_match': False,
            'details': {}
        }
        
        # Compare names (fuzzy matching)
        if cni_info['name'] and license_info['name']:
            cni_name = cni_info['name'].replace(' ', '').upper()
            license_name = license_info['name'].replace(' ', '').upper()
            comparison['name_match'] = cni_name == license_name
            comparison['details']['name'] = {
                'cni': cni_info['name'],
                'license': license_info['name'],
                'match': comparison['name_match']
            }
        
        # Compare first names
        if cni_info['first_name'] and license_info['first_name']:
            cni_fname = cni_info['first_name'].replace(' ', '').upper()
            license_fname = license_info['first_name'].replace(' ', '').upper()
            comparison['first_name_match'] = cni_fname == license_fname
            comparison['details']['first_name'] = {
                'cni': cni_info['first_name'],
                'license': license_info['first_name'],
                'match': comparison['first_name_match']
            }
        
        # Compare birth dates
        if cni_info['birth_date'] and license_info['birth_date']:
            comparison['birth_date_match'] = cni_info['birth_date'] == license_info['birth_date']
            comparison['details']['birth_date'] = {
                'cni': cni_info['birth_date'],
                'license': license_info['birth_date'],
                'match': comparison['birth_date_match']
            }
        
        # Compare sex
        if cni_info['sex'] and license_info['sex']:
            comparison['sex_match'] = cni_info['sex'] == license_info['sex']
            comparison['details']['sex'] = {
                'cni': cni_info['sex'],
                'license': license_info['sex'],
                'match': comparison['sex_match']
            }
        
        # Calculate overall match
        matches = sum([
            comparison['name_match'],
            comparison['first_name_match'],
            comparison['birth_date_match'],
            comparison['sex_match']
        ])
        total = 4
        comparison['overall_match'] = matches >= 3  # At least 3 out of 4 must match
        
        return comparison
    
    def validate_vehicle_photo(self, vehicle_photo_path):
        """Validate vehicle photo for license plate visibility"""
        text = self.extract_text_from_image(vehicle_photo_path)
        if not text:
            return {
                'plate_detected': False,
                'plate_number': None,
                'confidence': 0.0,
                'message': 'Unable to extract text from vehicle photo'
            }
        
        plate, confidence = self.detect_license_plate(text)
        
        return {
            'plate_detected': plate is not None,
            'plate_number': plate,
            'confidence': confidence,
            'message': 'License plate detected' if plate else 'License plate not clearly visible'
        }
