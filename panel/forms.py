from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from quiz.models import Language, Option, Package, Part, Question, TestSession


class StyledMixin:
    def _style(self):
        for name, f in self.fields.items():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "check")
            elif isinstance(w, forms.ClearableFileInput):
                w.attrs.setdefault("class", "input file")
            else:
                w.attrs.setdefault("class", "input")


class PackageForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Package
        fields = ["name", "description", "is_active", "shuffle_questions"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


class PartForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Part
        fields = ["order", "title_ru", "title_en", "instruction_ru", "instruction_en"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


class QuestionForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Question
        fields = ["order", "text_ru", "text_en", "image", "is_active"]
        widgets = {
            "text_ru": forms.Textarea(attrs={"rows": 3}),
            "text_en": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


class OptionForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Option
        fields = ["text_ru", "text_en", "is_correct"]
        widgets = {
            "text_ru": forms.TextInput(attrs={"placeholder": "Вариант ответа"}),
            "text_en": forms.TextInput(attrs={"placeholder": "Answer option"}),
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._style()


class BaseOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        alive = [
            f for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE")
        ]
        if len(alive) < 2:
            raise forms.ValidationError("Kamida 2 ta javob varianti bo'lishi kerak.")
        if len(alive) > 10:
            raise forms.ValidationError("Ko'pi bilan 10 ta variant bo'lishi mumkin.")
        correct = sum(1 for f in alive if f.cleaned_data.get("is_correct"))
        if correct != 1:
            raise forms.ValidationError("Aynan bitta to'g'ri javob belgilanishi kerak.")

    def save(self, commit=True):
        objs = super().save(commit=commit)
        # Variantlar tartibini forma tartibi bo'yicha qayta raqamlaymiz
        if commit:
            n = 1
            for f in self.forms:
                if f.instance.pk and not (f.cleaned_data or {}).get("DELETE"):
                    if f.instance.order != n:
                        f.instance.order = n
                        f.instance.save(update_fields=["order"])
                    n += 1
        return objs


def option_formset(extra):
    return inlineformset_factory(
        Question,
        Option,
        form=OptionForm,
        formset=BaseOptionFormSet,
        extra=extra,
        can_delete=True,
        max_num=10,
    )


class ResultFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Ism, familiya, telefon yoki ID"}))
    package = forms.ModelChoiceField(queryset=Package.objects.all(), required=False, empty_label="Barcha paketlar")
    language = forms.ChoiceField(choices=[("", "Barcha tillar")] + list(Language.choices), required=False)
    status = forms.ChoiceField(choices=[("", "Barcha holatlar")] + list(TestSession.Status.choices), required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    min_pct = forms.IntegerField(required=False, min_value=0, max_value=100, widget=forms.NumberInput(attrs={"placeholder": "Min %"}))

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "input")
