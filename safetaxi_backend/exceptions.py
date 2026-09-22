from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status
from django.http import JsonResponse


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_message = _extract_error_message(exc, response)
        custom_data = {
            'success': False,
            'error': error_message,
            'data': None,
        }
        response.data = custom_data
        return response

    error_message = str(exc) if str(exc) else 'Internal Server Error'
    return JsonResponse(
        {
            'success': False,
            'error': error_message,
            'data': None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_error_message(exc, response):
    if isinstance(exc, APIException):
        detail = exc.detail
        if isinstance(detail, dict):
            errors = []
            for field, messages in detail.items():
                if isinstance(messages, list):
                    for msg in messages:
                        errors.append(f"{field}: {msg}" if field != 'non_field_errors' else str(msg))
                else:
                    errors.append(f"{field}: {messages}" if field != 'non_field_errors' else str(messages))
            return '; '.join(errors) if errors else 'Validation error'
        elif isinstance(detail, list):
            return '; '.join(str(m) for m in detail)
        else:
            return str(detail)

    data = response.data
    if isinstance(data, dict) and 'detail' in data:
        return str(data['detail'])
    if isinstance(data, str):
        return data
    return 'An error occurred'
