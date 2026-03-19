from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Contact

@login_required
def contact_list(request):
    contacts = Contact.objects.all().order_by('-created_at')
    
    # Search
    query = request.GET.get('q')
    if query:
        contacts = contacts.filter(
            Q(name__icontains=query) | 
            Q(email__icontains=query) | 
            Q(phone__icontains=query) | 
            Q(code__icontains=query) |
            Q(pan_vat_number__icontains=query)
        )
    
    # Filter by type
    contact_type = request.GET.get('type')
    if contact_type in ['Customer', 'Supplier', 'Both']:
        contacts = contacts.filter(contact_type=contact_type)
        
    return render(request, 'contacts/contact_list.html', {
        'contacts': contacts,
        'query': query,
        'current_type': contact_type
    })

@login_required
def contact_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_type = request.POST.get('contact_type')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        pan_vat = request.POST.get('pan_vat')
        
        try:
            Contact.objects.create(
                name=name,
                contact_type=contact_type,
                email=email,
                phone=phone,
                address=address,
                pan_vat_number=pan_vat,
                created_by=request.user
            )
            messages.success(request, f"Contact {name} created successfully.")
            return redirect('contacts:contact_list')
        except Exception as e:
            messages.error(request, f"Error creating contact: {e}")
            
    return render(request, 'contacts/contact_create.html')

@login_required
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        contact.name = request.POST.get('name')
        contact.contact_type = request.POST.get('contact_type')
        contact.email = request.POST.get('email')
        contact.phone = request.POST.get('phone')
        contact.address = request.POST.get('address')
        contact.pan_vat_number = request.POST.get('pan_vat')
        contact.save()
        messages.success(request, f"Contact {contact.name} updated.")
        return redirect('contacts:contact_list')
    
    return render(request, 'contacts/contact_edit.html', {'contact': contact})
