import os
from .models import ShiftHandoff
from biometric.services import verify_face


def verify_handoff_biometric(handoff: ShiftHandoff):
    """Verify biometric match for shift handoff.
    
    Compares outgoing driver's reference photo with incoming driver's selfie
    to ensure the incoming driver is the authorized person.
    """
    if not handoff.outgoing_selfie or not handoff.incoming_selfie:
        return {
            'match': False,
            'confidence': 0.0,
            'reason': 'Missing selfie images'
        }
    
    # Get outgoing driver's reference photo from their profile
    try:
        outgoing_driver_profile = handoff.outgoing_driver.driver_profile
        reference_photo = outgoing_driver_profile.profile_photo
    except Exception:
        return {
            'match': False,
            'confidence': 0.0,
            'reason': 'Outgoing driver has no reference photo'
        }
    
    if not reference_photo:
        return {
            'match': False,
            'confidence': 0.0,
            'reason': 'Outgoing driver has no reference photo'
        }
    
    # Verify faces using the biometric service
    result = verify_face(
        handoff.incoming_selfie.path,
        reference_photo.path
    )
    
    return result
