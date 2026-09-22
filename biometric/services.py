import os
import json
import requests
import boto3
from botocore.exceptions import ClientError


def verify_face_aws(selfie_path, reference_path=None):
    """Verify face using AWS Rekognition.
    
    Requires AWS credentials configured in environment or ~/.aws/credentials.
    """
    try:
        client = boto3.client('rekognition')
        
        # Read selfie image
        with open(selfie_path, 'rb') as image_file:
            selfie_bytes = image_file.read()
        
        # If reference provided, compare faces
        if reference_path and os.path.exists(reference_path):
            with open(reference_path, 'rb') as ref_file:
                reference_bytes = ref_file.read()
            
            response = client.compare_faces(
                SourceImage={'Bytes': reference_bytes},
                TargetImage={'Bytes': selfie_bytes},
                SimilarityThreshold=80
            )
            
            if response['FaceMatches']:
                similarity = response['FaceMatches'][0]['Similarity']
                return {
                    'match': True,
                    'confidence': similarity / 100.0,
                    'reason': f'Faces match with {similarity:.1f}% similarity',
                    'raw': response
                }
            else:
                return {
                    'match': False,
                    'confidence': 0.0,
                    'reason': 'Faces do not match',
                    'raw': response
                }
        else:
            # Just detect face in selfie
            response = client.detect_faces(
                Image={'Bytes': selfie_bytes},
                Attributes=['ALL']
            )
            
            if response['FaceDetails']:
                return {
                    'match': True,
                    'confidence': response['FaceDetails'][0]['Confidence'] / 100.0,
                    'reason': 'Face detected successfully',
                    'raw': response
                }
            else:
                return {
                    'match': False,
                    'confidence': 0.0,
                    'reason': 'No face detected',
                    'raw': response
                }
                
    except ClientError as e:
        return {
            'match': False,
            'confidence': 0.0,
            'reason': f'AWS error: {str(e)}'
        }
    except Exception as e:
        return {
            'match': False,
            'confidence': 0.0,
            'reason': f'Error: {str(e)}'
        }


def verify_face(selfie_path, reference_path=None):
    """Pluggable biometric verification.

    Behaviour:
    - If `BIOMETRIC_PROVIDER` == 'aws', use AWS Rekognition
    - If `BIOMETRIC_PROVIDER` == 'http_api', forward files to `BIOMETRIC_API_URL` with optional API key.
    - Otherwise, use a simple local placeholder.

    Returns a dict with at least `match` (bool) and `confidence` (float).
    """
    provider = os.getenv('BIOMETRIC_PROVIDER', 'mock')
    
    if provider == 'aws':
        return verify_face_aws(selfie_path, reference_path)
    
    if provider == 'http_api':
        url = os.getenv('BIOMETRIC_API_URL')
        api_key = os.getenv('BIOMETRIC_API_KEY')
        if not url:
            return {'match': False, 'confidence': 0.0, 'reason': 'no provider url configured'}

        files = {}
        try:
            if selfie_path and os.path.exists(selfie_path):
                files['selfie'] = open(selfie_path, 'rb')
            if reference_path and os.path.exists(reference_path):
                files['reference'] = open(reference_path, 'rb')

            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            resp = requests.post(url, files=files, headers=headers, timeout=30)
            for f in files.values():
                try:
                    f.close()
                except Exception:
                    pass

            if resp.status_code != 200:
                return {'match': False, 'confidence': 0.0, 'reason': f'provider error {resp.status_code}'}
            data = resp.json()
            # Expect provider to return {match:bool, confidence:float}
            return {
                'match': bool(data.get('match')), 
                'confidence': float(data.get('confidence', 0.0)),
                'raw': data,
            }
        except Exception as e:
            return {'match': False, 'confidence': 0.0, 'reason': str(e)}

    # mock provider fallback
    if reference_path and os.path.exists(reference_path):
        return {'match': True, 'confidence': 0.92, 'reason': 'mock-match'}
    return {'match': False, 'confidence': 0.0, 'reason': 'no reference provided'}
