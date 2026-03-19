from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee

@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by('employee_id')
    return render(request, 'hr/employee_list.html', {'employees': employees})

@login_required
def employee_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        designation = request.POST.get('designation')
        department = request.POST.get('department')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        pan_number = request.POST.get('pan_number')
        basic_salary = request.POST.get('basic_salary', 0)
        join_date = request.POST.get('join_date') or None
        
        Employee.objects.create(
            name=name,
            designation=designation,
            department=department,
            email=email,
            phone=phone,
            address=address,
            pan_number=pan_number,
            basic_salary=basic_salary,
            join_date=join_date,
            created_by=request.user
        )
        messages.success(request, f"Employee {name} created successfully.")
        return redirect('hr:employee_list')
    return render(request, 'hr/employee_form.html')

@login_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.designation = request.POST.get('designation')
        employee.department = request.POST.get('department')
        employee.email = request.POST.get('email')
        employee.phone = request.POST.get('phone')
        employee.address = request.POST.get('address')
        employee.pan_number = request.POST.get('pan_number')
        employee.basic_salary = request.POST.get('basic_salary', 0)
        join_date = request.POST.get('join_date')
        employee.join_date = join_date if join_date else None
        
        employee.save()
        messages.success(request, f"Employee {employee.name} updated successfully.")
        return redirect('hr:employee_list')
    return render(request, 'hr/employee_form.html', {'employee': employee})

@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.is_active = False
        employee.save()
        messages.success(request, f"Employee {employee.name} deactivated.")
        return redirect('hr:employee_list')
    return render(request, 'hr/employee_confirm_delete.html', {'employee': employee})
