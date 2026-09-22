from users.views import (
    UserViewSet,
    RegisterView,
    DriverProfileViewSet,
    LogoutView,
    SendOtpView,
    VerifyOtpView,
    ProfileView,
)
from taxis.views import TaxiViewSet
from trips.views import TripViewSet
from sos.views import IncidentViewSet
from documents.views import DriverDocumentViewSet
from ratings.views import RatingViewSet
from biometric.views import BiometricRequestViewSet
from notifications.views import DeviceViewSet
