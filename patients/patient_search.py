from django.db.models import Q

from .models import Patient


def patient_search_queryset(q: str):
    qs = Patient.objects.all()
    q = (q or "").strip()
    if not q:
        return qs
    filters = (
        Q(full_name__icontains=q)
        | Q(phone__icontains=q)
        | Q(region__icontains=q)
        | Q(address__icontains=q)
        | Q(father_name__icontains=q)
        | Q(profession__icontains=q)
    )
    if q.isdigit():
        filters |= Q(patient_nb=int(q))
    return qs.filter(filters)
