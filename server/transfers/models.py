from django.db import models
from django.utils import timezone
from users.models import User, Object
from tools.models import Tool

# -----------------------
# Статусы запроса передачи инструмента
# -----------------------
class RequestStatus(models.Model):
    """
    Статусы запроса на передачу инструмента.
    Примеры: Новый, Одобрен, Отклонён, Выполнен.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# -----------------------
# Заявка на передачу инструмента
# -----------------------
class ToolRequest(models.Model):
    """
    Заявка на передачу инструмента между объектами.
    """
    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name='tool_requests')
    from_object = models.ForeignKey(Object, on_delete=models.SET_NULL, null=True, blank=True, related_name='tool_requests_from')
    to_object = models.ForeignKey(Object, on_delete=models.PROTECT, related_name='tool_requests_to')
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tool_requests_requester')
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tool_requests_approver')
    status = models.ForeignKey(RequestStatus, on_delete=models.PROTECT, related_name='tool_requests')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.tool} запрос от {self.requester} на {self.to_object}"
