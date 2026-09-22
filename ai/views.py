import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from .serializers import RiskAnalysisSerializer, ChatMessageSerializer
import requests
import os


class DetectAnomalySerializer(serializers.Serializer):
    waypoints = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    expected_duration_minutes = serializers.FloatField(required=False, allow_null=True)
    actual_elapsed_minutes = serializers.FloatField(required=False, allow_null=True)
    speed_samples = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        default=list,
    )


def _haversine_km(lat1, lng1, lat2, lng2):
    lat1_rad, lng1_rad = math.radians(lat1), math.radians(lng1)
    lat2_rad, lng2_rad = math.radians(lat2), math.radians(lng2)
    dlon = lng2_rad - lng1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c


EMERGENCY_CONTACTS = {
    'police': '117',
    'gendarmerie': '117',
    'pompiers': '118',
    'samu': '119',
    'urgence': '112',
}

FALLBACK_CHAT_RESPONSES = [
    {
        'keywords': ['bonjour', 'salut', 'hello', 'hi', 'bonsoir'],
        'response': (
            "Bonjour ! Je suis votre assistant sécurité SafeTaxi. "
            "Comment puis-je vous aider aujourd'hui ? Vous pouvez me poser des questions sur "
            "les contacts d'urgence, les consignes de sécurité, ou me décrire une situation préoccupante."
        ),
    },
    {
        'keywords': ['urgence', 'urgent', 'aide', 'aider', 'secours', 'sos', 'danger'],
        'response': (
            "🚨 Si vous êtes en danger immédiat, composez immédiatement :\n"
            "• Police / Gendarmerie : **117**\n"
            "• Pompiers : **118**\n"
            "• SAMU (Urgences médicales) : **119**\n"
            "• Numéro d'urgence européen : **112**\n\n"
            "Utilisez également le bouton SOS de l'application pour alerter les autorités et vos proches."
        ),
    },
    {
        'keywords': ['police', 'gendarmerie', 'agent', 'commissariat'],
        'response': (
            "📞 Pour contacter la Police ou la Gendarmerie au Cameroun : **117**\n"
            "Ce numéro est gratuit et accessible 24h/24 depuis n'importe quel téléphone."
        ),
    },
    {
        'keywords': ['pompier', 'incendie', 'feu'],
        'response': (
            "🚒 Pour les pompiers au Cameroun : **118**\n"
            "Contactez-les en cas d'incendie, d'accident de la route ou d'intervention d'urgence."
        ),
    },
    {
        'keywords': ['medical', 'santé', 'malade', 'accident', 'blessé', 'samu', 'hôpital', 'hopital'],
        'response': (
            "🏥 Pour une urgence médicale (SAMU) au Cameroun : **119**\n"
            "Ce numéro vous met en relation avec les services médicaux d'urgence 24h/24.\n"
            "En cas d'accident de la route, composez également le 117 pour la police."
        ),
    },
    {
        'keywords': ['numéro', 'numero', 'contact', 'téléphone', 'telephone', 'appeler'],
        'response': (
            "📋 Contacts d'urgence au Cameroun :\n"
            "• Police / Gendarmerie : **117**\n"
            "• Pompiers : **118**\n"
            "• SAMU (Urgences médicales) : **119**\n"
            "• Urgence générale : **112**\n\n"
            "Notez ces numéros et partagez-les avec vos proches."
        ),
    },
    {
        'keywords': ['sécurité', 'securite', 'conseil', 'astuce', 'prudence'],
        'response': (
            "🛡️ Conseils sécurité pendant un trajet en taxi :\n"
            "1. Vérifiez l'identité du chauffeur et la plaque du véhicule avant de monter.\n"
            "2. Partagez votre trajet avec un proche via l'application.\n"
            "3. Gardez votre téléphone chargé et accessible.\n"
            "4. Notez les points de repère pendant le trajet.\n"
            "5. En cas de doute, utilisez le bouton SOS immédiatement.\n"
            "6. Évitez de voyager seul(e) tard le soir si possible.\n"
            "7. Vérifiez que les portes et fenêtres se ferment correctement."
        ),
    },
    {
        'keywords': ['taxi', 'chauffeur', 'conducteur', 'verifier', 'vérifier', 'vérification'],
        'response': (
            "✅ Avant de monter dans un taxi, vérifiez :\n"
            "• Le numéro de plaque correspond à celui affiché dans l'application\n"
            "• La photo du chauffeur correspond à la personne présente\n"
            "• Le véhicule est bien marqué comme taxi officiel\n"
            "• Le QR code du véhicule scanné correspond\n"
            "• Le chauffeur a un profil vérifié (badge vert)"
        ),
    },
    {
        'keywords': ['localisation', 'position', 'où', 'ou', 'où suis-je', 'ou suis je'],
        'response': (
            "📍 Votre position GPS est utilisée par l'application pour :\n"
            "• Permettre aux secours de vous localiser en cas d'alerte SOS\n"
            "• Partager votre trajet en temps réel avec vos contacts de confiance\n"
            "• Calculer votre itinéraire et estimer l'heure d'arrivée\n\n"
            "Pour signaler votre position manuellement, utilisez le bouton SOS qui enverra vos coordonnées GPS aux secours."
        ),
    },
    {
        'keywords': ['merci', 'thanks', 'thank you', 'ok', 'bien'],
        'response': (
            "Avec plaisir ! Restez prudent(e) et n'hésitez pas à utiliser le bouton SOS si vous vous sentez en danger. "
            "Bonne route avec SafeTaxi ! 🚖"
        ),
    },
]


def _fallback_french_response(user_message):
    if not user_message:
        return (
            "Bonjour ! Je suis votre assistant sécurité SafeTaxi. "
            "Posez-moi une question sur la sécurité, les contacts d'urgence ou le fonctionnement de l'application."
        )

    msg_lower = user_message.lower()

    for rule in FALLBACK_CHAT_RESPONSES:
        if any(kw in msg_lower for kw in rule['keywords']):
            return rule['response']

    return (
        "Je suis votre assistant sécurité SafeTaxi. Voici ce sur quoi je peux vous aider :\n"
        "• Numéros d'urgence au Cameroun (Police 117, Pompiers 118, SAMU 119)\n"
        "• Conseils de sécurité pendant un trajet\n"
        "• Vérifications avant de monter dans un taxi\n"
        "• Utilisation de l'alerte SOS\n\n"
        "Décrivez votre question ou votre situation, je ferai de mon mieux pour vous répondre."
    )


class AIViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def analyze_risk(self, request):
        """Analyze risk based on location, time, and context using Qwen AI"""
        serializer = RiskAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.validated_data['location']
        time = serializer.validated_data['time']
        weather = serializer.validated_data.get('weather', 'unknown')
        additional_context = serializer.validated_data.get('additional_context', '')

        prompt = f"""Analyze the safety risk for a taxi trip with the following details:
- Location: {location}
- Time: {time}
- Weather: {weather}
- Additional context: {additional_context}

Provide a risk assessment on a scale of 1-10 (1 being very safe, 10 being very dangerous),
along with specific safety recommendations and potential hazards to watch out for.
Format your response as JSON with keys: risk_score, risk_level, recommendations, hazards."""

        qwen_api_key = os.getenv('QWEN_API_KEY', '')
        if not qwen_api_key:
            risk_score = self._basic_risk_analysis(time, weather)
            return Response({
                'risk_score': risk_score,
                'risk_level': self._get_risk_level(risk_score),
                'recommendations': self._get_basic_recommendations(risk_score),
                'hazards': self._get_basic_hazards(weather),
                'source': 'basic_analysis'
            })

        try:
            response = requests.post(
                'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {qwen_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'qwen-turbo',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7
                }
            )

            if response.status_code == 200:
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content']
                return Response({
                    'analysis': content,
                    'source': 'qwen_ai'
                })
            else:
                raise Exception(f"Qwen API error: {response.status_code}")

        except Exception as e:
            risk_score = self._basic_risk_analysis(time, weather)
            return Response({
                'risk_score': risk_score,
                'risk_level': self._get_risk_level(risk_score),
                'recommendations': self._get_basic_recommendations(risk_score),
                'hazards': self._get_basic_hazards(weather),
                'source': 'basic_analysis_fallback',
                'error': str(e)
            })

    @action(detail=False, methods=['post'])
    def chat(self, request):
        """Chat with AI assistant for safety advice and information"""
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        messages = serializer.validated_data['messages']

        qwen_api_key = os.getenv('QWEN_API_KEY', '')
        if not qwen_api_key:
            last_user_message = ''
            if messages and isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        content = msg.get('content', '')
                        if isinstance(content, str):
                            last_user_message = content
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and part.get('type') == 'text':
                                    last_user_message = part.get('text', '')
                                    break
                        if last_user_message:
                            break

            fallback_text = _fallback_french_response(last_user_message)
            return Response({
                'response': fallback_text,
                'source': 'french_fallback_assistant',
                'emergency_contacts': EMERGENCY_CONTACTS,
            })

        try:
            response = requests.post(
                'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {qwen_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'qwen-turbo',
                    'messages': messages,
                    'temperature': 0.7
                }
            )

            if response.status_code == 200:
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content']
                return Response({
                    'response': content,
                    'source': 'qwen_ai'
                })
            else:
                last_user_message = ''
                if messages and isinstance(messages, list):
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            last_user_message = msg.get('content', '')
                            if isinstance(last_user_message, str):
                                break
                fallback_text = _fallback_french_response(last_user_message)
                return Response({
                    'response': fallback_text,
                    'source': 'french_fallback_assistant',
                    'emergency_contacts': EMERGENCY_CONTACTS,
                    'api_error': f'Qwen API HTTP {response.status_code}'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            last_user_message = ''
            if messages and isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('role') == 'user':
                        last_user_message = msg.get('content', '')
                        if isinstance(last_user_message, str):
                            break
            fallback_text = _fallback_french_response(last_user_message)
            return Response({
                'response': fallback_text,
                'source': 'french_fallback_assistant',
                'emergency_contacts': EMERGENCY_CONTACTS,
                'error': str(e)
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='detect-anomaly')
    def detect_anomaly(self, request):
        """Detect trip anomalies using heuristics (Qwen AI used if available)"""
        serializer = DetectAnomalySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        waypoints = serializer.validated_data.get('waypoints') or []
        expected_duration = serializer.validated_data.get('expected_duration_minutes')
        actual_elapsed = serializer.validated_data.get('actual_elapsed_minutes')
        speed_samples = serializer.validated_data.get('speed_samples') or []

        reasons = []
        anomaly_score = 0.0

        if expected_duration and actual_elapsed and expected_duration > 0:
            ratio = actual_elapsed / expected_duration
            if ratio > 1.5:
                score_contrib = min(60.0, (ratio - 1.5) * 120)
                anomaly_score += score_contrib
                reasons.append(
                    f"Durée de trajet anormale : {actual_elapsed:.0f} min pour {expected_duration:.0f} min attendues "
                    f"(rapport x{ratio:.2f}, seuil x1.5)"
                )
            elif ratio > 1.2:
                anomaly_score += 15.0
                reasons.append(
                    f"Durée de trajet plus longue que prévue : {actual_elapsed:.0f} min pour {expected_duration:.0f} min attendues"
                )

        if len(waypoints) >= 2:
            try:
                route_points = []
                for wp in waypoints:
                    if isinstance(wp, dict) and 'lat' in wp and 'lng' in wp:
                        try:
                            route_points.append((float(wp['lat']), float(wp['lng'])))
                        except (TypeError, ValueError):
                            continue

                if len(route_points) >= 2:
                    total_actual = 0.0
                    for i in range(len(route_points) - 1):
                        lat1, lng1 = route_points[i]
                        lat2, lng2 = route_points[i + 1]
                        total_actual += _haversine_km(lat1, lng1, lat2, lng2)

                    start_lat, start_lng = route_points[0]
                    end_lat, end_lng = route_points[-1]
                    direct_distance = _haversine_km(start_lat, start_lng, end_lat, end_lng)

                    if direct_distance > 0 and total_actual > 0:
                        detour_ratio = total_actual / max(0.001, direct_distance)
                        if detour_ratio > 1.5:
                            score_contrib = min(50.0, (detour_ratio - 1.5) * 80)
                            anomaly_score += score_contrib
                            reasons.append(
                                f"Déviation d'itinéraire détectée : chemin parcouru {total_actual:.1f} km "
                                f"pour {direct_distance:.1f} km à vol d'oiseau (rapport x{detour_ratio:.2f})"
                            )
                        elif detour_ratio > 1.3:
                            anomaly_score += 10.0
                            reasons.append(
                                f"Légère déviation d'itinéraire : chemin parcouru {total_actual:.1f} km "
                                f"pour {direct_distance:.1f} km à vol d'oiseau"
                            )

                    if len(route_points) >= 4 and direct_distance > 0.1:
                        dists_from_direct = []
                        for (lat, lng) in route_points[1:-1]:
                            from math import radians, sin, cos, atan2, sqrt
                            d1 = _haversine_km(start_lat, start_lng, lat, lng)
                            d2 = _haversine_km(lat, lng, end_lat, end_lng)
                            s = (d1 + d2 + direct_distance) / 2.0
                            area_sq = max(0.0, s * (s - d1) * (s - d2) * (s - direct_distance))
                            altitude = (2.0 * math.sqrt(area_sq)) / max(0.001, direct_distance)
                            dists_from_direct.append(altitude)

                        if dists_from_direct:
                            max_dev = max(dists_from_direct)
                            if max_dev > 1.0:
                                score_contrib = min(40.0, (max_dev - 1.0) * 40)
                                anomaly_score += score_contrib
                                reasons.append(
                                    f"Écart maximal de l'itinéraire : {max_dev:.2f} km (seuil 1 km)"
                                )
            except Exception as calc_e:
                reasons.append(f"Calcul d'itinéraire partiellement indisponible: {calc_e}")

        if speed_samples:
            try:
                valid_speeds = [float(s) for s in speed_samples if isinstance(s, (int, float))]
                if valid_speeds:
                    max_speed = max(valid_speeds)
                    if max_speed > 130:
                        anomaly_score += 25.0
                        reasons.append(f"Vitesse excessive détectée : {max_speed:.0f} km/h (seuil 130 km/h)")
                    elif max_speed > 110:
                        anomaly_score += 10.0
                        reasons.append(f"Vitesse élevée : {max_speed:.0f} km/h")

                    if len(valid_speeds) >= 5:
                        avg_speed = sum(valid_speeds) / len(valid_speeds)
                        if avg_speed < 5 and actual_elapsed and actual_elapsed > 10:
                            anomaly_score += 15.0
                            reasons.append(
                                f"Vitesse moyenne anormalement basse : {avg_speed:.0f} km/h sur {actual_elapsed:.0f} min"
                            )
            except (TypeError, ValueError):
                pass

        qwen_api_key = os.getenv('QWEN_API_KEY', '')
        ai_analysis = None
        if qwen_api_key:
            try:
                prompt = f"""Analyse this taxi trip data for anomalies in French or English:
Waypoints count: {len(waypoints)}
Expected duration: {expected_duration} min
Actual elapsed: {actual_elapsed} min
Speed samples count: {len(speed_samples)}

Reasons already found: {reasons}
Anomaly score so far (0-100): {anomaly_score}

Respond with JSON: {{
  "anomaly_score": (0-100),
  "is_anomaly": true/false,
  "severity": "low"/"medium"/"high"/"critical",
  "recommendations": [array of strings],
  "additional_notes": "str"
}}"""
                ai_resp = requests.post(
                    'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {qwen_api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'qwen-turbo',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'temperature': 0.1
                    },
                    timeout=8,
                )
                if ai_resp.status_code == 200:
                    ai_analysis = ai_resp.json()['choices'][0]['message']['content']
            except Exception:
                ai_analysis = None

        anomaly_score = min(100.0, max(0.0, anomaly_score))

        if anomaly_score >= 80:
            severity = 'critical'
            is_anomaly = True
        elif anomaly_score >= 55:
            severity = 'high'
            is_anomaly = True
        elif anomaly_score >= 30:
            severity = 'medium'
            is_anomaly = True
        elif anomaly_score >= 10:
            severity = 'low'
            is_anomaly = False
        else:
            severity = 'none'
            is_anomaly = False

        recommendations = []
        if is_anomaly:
            recommendations.append("Surveiller attentivement ce trajet")
            if anomaly_score >= 55:
                recommendations.append("Contacter le passager et le chauffeur pour vérification")
                recommendations.append("Envisager de déclencher une alerte de niveau sécurité")
            if any('durée' in r.lower() or 'duration' in r.lower() for r in reasons):
                recommendations.append("Vérifier la raison du retard (embouteillage, déviation autorisée, etc.)")
            if any('vitesse' in r.lower() or 'speed' in r.lower() or 'déviation' in r.lower() or 'deviation' in r.lower() for r in reasons):
                recommendations.append("Vérifier que le chauffeur suit bien l'itinéraire prévu")
        else:
            recommendations.append("Trajet dans les normes habituelles")

        result = {
            'anomaly_score': round(anomaly_score, 2),
            'is_anomaly': is_anomaly,
            'severity': severity,
            'reasons': reasons,
            'recommendations': recommendations,
            'source': 'heuristic' if not qwen_api_key else ('heuristic_with_qwen_fallback' if not ai_analysis else 'qwen_with_heuristic'),
        }
        if ai_analysis:
            result['ai_analysis'] = ai_analysis

        return Response(result)

    def _basic_risk_analysis(self, time, weather):
        risk_score = 3

        if 'night' in time.lower() or 'evening' in time.lower():
            risk_score += 2
        if 'midnight' in time.lower() or 'late' in time.lower():
            risk_score += 2

        if 'rain' in weather.lower():
            risk_score += 2
        if 'storm' in weather.lower() or 'thunder' in weather.lower():
            risk_score += 3
        if 'fog' in weather.lower():
            risk_score += 2

        return min(10, max(1, risk_score))

    def _get_risk_level(self, score):
        if score <= 2:
            return 'Very Low'
        elif score <= 4:
            return 'Low'
        elif score <= 6:
            return 'Medium'
        elif score <= 8:
            return 'High'
        else:
            return 'Very High'

    def _get_basic_recommendations(self, score):
        recommendations = []
        if score >= 5:
            recommendations.append('Share your trip details with someone')
            recommendations.append('Keep your phone charged and accessible')
        if score >= 7:
            recommendations.append('Use the SOS feature if you feel unsafe')
            recommendations.append('Verify the driver and taxi before boarding')
        if score >= 9:
            recommendations.append('Consider postponing your trip if possible')
            recommendations.append('Use trusted taxi services with verified drivers')
        return recommendations

    def _get_basic_hazards(self, weather):
        hazards = []
        if 'rain' in weather.lower():
            hazards.append('Slippery roads')
            hazards.append('Reduced visibility')
        if 'fog' in weather.lower():
            hazards.append('Poor visibility')
            hazards.append('Difficulty identifying landmarks')
        if 'storm' in weather.lower():
            hazards.append('Dangerous road conditions')
            hazards.append('Potential for vehicle breakdown')
        return hazards
