from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "placeholder": "Напишіть свій коментар...",
                "rows": 4,
                "class": "comment-textarea",
            }),
        }
        labels = {"text": "Ваш коментар"}
