from django import forms
from django.core.exceptions import ValidationError

from .models import Question, Parish, Inspection, GeneralComment, InspectionQuestion, InspectionImage


class ParishForm(forms.ModelForm):
    class Meta:
        model = Parish
        fields = ['image', 'name', 'description', 'location', 'contact', 'phone_number']

    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control'}))
    location = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))  # New field
    contact = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))  # New field
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = []  # Keep empty, as we will add fields dynamically

    comment_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="General Comment"
    )
    uploaded_images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}),
        label="Upload Images"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inspection_instance = kwargs.get('instance')
        existing_question_ids = set()

        # Dynamically add fields for questions already linked to this inspection
        if inspection_instance:
            inspection_questions = InspectionQuestion.objects.filter(
                inspection=inspection_instance,
                question__deleted=False  # Exclude deleted questions
            )
            for inspection_question in inspection_questions:
                question = inspection_question.question
                field_name = f'question_{question.id}'
                self.fields[field_name] = forms.ChoiceField(
                    label=question.question_text,  # Use specific text if modified
                    choices=[('yes', 'Yes'), ('no', 'No'), ('other', 'Other')],
                    widget=forms.RadioSelect(),
                    required=False,
                )
                # Set initial value for the response
                self.fields[field_name].initial = inspection_question.answer
                existing_question_ids.add(question.id)

        # Add fields for any default questions not linked to this inspection
        default_questions = Question.objects.filter(is_default=True).exclude(id__in=existing_question_ids)
        for question in default_questions:
            field_name = f'question_{question.id}'
            self.fields[field_name] = forms.ChoiceField(
                label=question.question_text,
                choices=[('yes', 'Yes'), ('no', 'No'), ('other', 'Other')],
                widget=forms.RadioSelect(),
                required=False,
            )

        # Set initial value for the general comment field
        general_comment = GeneralComment.objects.filter(
            inspection=inspection_instance).first() if inspection_instance else None
        self.fields['comment_text'].initial = general_comment.comment_text if general_comment else ""

        # Ensure the `comment_text` field is ordered last
        self.order_fields(field_order=[field for field in self.fields if field != 'comment_text'] + ['comment_text'])

    def clean_uploaded_images(self):
        """Validate that no more than 5 images are uploaded."""
        images = self.files.getlist('uploaded_images')
        if len(images) > 5:
            raise ValidationError("You can only upload up to 5 images.")
        return images

    def save(self, commit=True):
        """Handle saving of images and general comment."""
        inspection = super().save(commit=commit)
        general_comment_text = self.cleaned_data.get('comment_text', "")
        uploaded_images = self.cleaned_data.get('uploaded_images', [])

        # CODE FOR FUTURE REFERENCES
        # Save the general comment
        # general_comment, _ = GeneralComment.objects.get_or_create(inspection=inspection)
        # general_comment.comment_text = general_comment_text
        # general_comment.save()
        # print(uploaded_images)
        # for upload_image in uploaded_images:
        #     InspectionImage.objects.create(inspection=inspection, image=upload_image).save()

        return inspection


class InspectionQuestionForm(forms.ModelForm):
    class Meta:
        model = InspectionQuestion
        fields = ['answer']  # Only allow editing of the answer
