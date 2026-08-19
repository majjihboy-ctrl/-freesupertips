from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        # UserCreationForm doesn't enforce email uniqueness on its own.
        # Without this, two accounts could share an email, which would
        # make password reset ambiguous (Django resets every account tied
        # to that address) and generally breaks the "one email = one
        # account" assumption the rest of the app relies on.
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email