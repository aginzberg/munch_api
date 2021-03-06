from rest_framework import status, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from munch.models import Promotion
from munch.permissions.user import IsRestaurant
from munch.permissions.promotion import IsPromotionOwner
from munch.serializers.promotion import *
from datetime import datetime
from oauth2_provider.ext.rest_framework import OAuth2Authentication
from django.db.models import Count


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.filter(deleted=False)
    serializer_class = PromotionSerializer
    permission_classes = [IsRestaurant, IsPromotionOwner, IsAuthenticated]

    def create(self, request, *args, **kwargs):
        promotion_serializer = PromotionSerializer(data=request.data, partial=True)
        if promotion_serializer.is_valid():
            data = promotion_serializer.create(restaurant=request.user.restaurant)
            response_data = {
                "id": data.id
            }
            return Response(data=response_data, status=status.HTTP_200_OK)
        else:
            return Response(data=promotion_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        promotion_serializer = PromotionSerializer(instance=instance, data=request.data, partial=True)
        if promotion_serializer.is_valid():
            promotion_serializer.update(instance, promotion_serializer.validated_data)
            return Response(data={"message": "Promotion updated successfully!"}, status=status.HTTP_200_OK)
        else:
            return Response(data=promotion_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        promotion_serializer = PromotionSerializer(instance=instance)
        promotion_serializer.delete(instance)
        return Response(data={"message": "Promotion deleted successfully"}, status=status.HTTP_200_OK)

    @list_route(methods=['get'], permission_classes=[IsAuthenticated], url_path='list_promotions')
    def list_promotions(self, request, *args, **kwargs):
        query = '''
                SELECT DISTINCT p.*, 
                       CASE WHEN sub.num_claimed IS NULL 
                       THEN 0 ELSE sub.num_claimed END num_claims
                FROM munch_promotion p
                LEFT OUTER JOIN (
                    SELECT promotion_id, COUNT(*) num_claimed
                    FROM munch_claim c 
                    INNER JOIN munch_promotion p ON c.promotion_id=p.id
                    GROUP BY promotion_id
                ) sub 
                ON p.id=promotion_id 
                '''
        promotions = Promotion.objects.raw(query)
        promotion_serializer = PromotionSerializer(instance=promotions, many=True, 
                                                   context={'customer_id': request.user.customer.id},
                                                   fields=('id', 'text', 'repetition', 'restaurant',
                                                           'expiration', 'retail_value', 'rating', 'num_claims',
                                                           'deleted'))
        return Response(data=promotion_serializer.data, status=status.HTTP_200_OK)

    @list_route(methods=['get'], permission_classes=[IsAuthenticated, IsRestaurant],
                url_path='details')
    def details(self, request, *args, **kwargs):
        query = '''
                    SELECT p.id, 
                           COUNT(CASE WHEN is_redeemed='f' THEN 1 END) claimed,
                           COUNT(CASE WHEN is_redeemed='t' THEN 1 END) redeemed 
                    FROM munch_promotion p
                    LEFT OUTER JOIN munch_claim c ON c.promotion_id=p.id
                    WHERE p.restaurant_id=%(restaurant)s
                    GROUP BY p.id
                '''
        promotions = Promotion.objects.raw(query, params={'restaurant': request.user.restaurant.id})
        promotion_serializer = PromotionSerializer(instance=promotions, many=True,
                                                   fields=('id', 'claimed', 'redeemed',))
        return Response(data=promotion_serializer.data, status=status.HTTP_200_OK)

