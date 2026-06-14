from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import Group, GroupMembership
from .serializers import GroupSerializer, CreateGroupSerializer
from users.models import User


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def groups_list(request):
    if request.method == 'GET':
        memberships = GroupMembership.objects.filter(user=request.user, is_active=True)
        groups = [m.group for m in memberships]
        return Response(GroupSerializer(groups, many=True).data)

    if request.method == 'POST':
        serializer = CreateGroupSerializer(data=request.data)
        if serializer.is_valid():
            group = serializer.save(created_by=request.user)
            GroupMembership.objects.create(
                group=group,
                user=request.user,
                joined_at=timezone.now().date(),
                is_active=True
            )
            return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def group_detail(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(GroupSerializer(group).data)

    if request.method == 'PUT':
        serializer = CreateGroupSerializer(group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(GroupSerializer(group).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_member(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get('user_id')
    joined_at = request.data.get('joined_at', timezone.now().date())

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    membership, created = GroupMembership.objects.get_or_create(
        group=group,
        user=user,
        defaults={'joined_at': joined_at, 'is_active': True}
    )
    if not created:
        membership.is_active = True
        membership.joined_at = joined_at
        membership.left_at = None
        membership.save()

    return Response({'message': f'{user.username} added to {group.name}'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_member(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    user_id = request.data.get('user_id')
    left_at = request.data.get('left_at', timezone.now().date())

    try:
        membership = GroupMembership.objects.get(group=group, user_id=user_id)
        membership.is_active = False
        membership.left_at = left_at
        membership.save()
        return Response({'message': 'Member removed'})
    except GroupMembership.DoesNotExist:
        return Response({'error': 'Membership not found'}, status=status.HTTP_404_NOT_FOUND)
