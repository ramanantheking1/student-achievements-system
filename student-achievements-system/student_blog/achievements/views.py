from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from .models import Achievement, StudentProfile, ContactMessage
from .forms import AchievementForm, UserRegistrationForm, ProfileForm
from .admin_auth import staff_required, superuser_required

def home(request):
    """Home page with featured achievements"""
    try:
        featured_achievements = Achievement.objects.filter(is_approved=True).order_by('-created_at')[:6]
        total_achievements = Achievement.objects.filter(is_approved=True).count()
        total_students = User.objects.filter(is_staff=False).count()
    except Exception as e:
        featured_achievements = []
        total_achievements = 0
        total_students = 0
    
    context = {
        'featured_achievements': featured_achievements,
        'total_achievements': total_achievements,
        'total_students': total_students,
    }
    return render(request, 'achievements/home.html', context)

def achievements(request):
    """All achievements page"""
    search_query = request.GET.get('search', '')
    
    try:
        all_achievements = Achievement.objects.filter(is_approved=True).order_by('-created_at')
        
        if search_query:
            all_achievements = all_achievements.filter(
                Q(name__icontains=search_query) |
                Q(event__icontains=search_query) |
                Q(competition__icontains=search_query) |
                Q(description__icontains=search_query)
            )
    except Exception as e:
        all_achievements = []
    
    context = {
        'achievements': all_achievements,
        'search_query': search_query,
    }
    return render(request, 'achievements/achievements.html', context)

def signup(request):
    """Student registration - only creates student accounts"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Auto login after signup
                login(request, user)
                messages.success(request, '🎉 Registration successful! Welcome to CSE Achievers!')
                return redirect('dashboard')
                
            except Exception as e:
                messages.error(request, f'❌ Error creating account: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'achievements/signup.html', {'form': form})

def login_view(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'👋 Welcome back, {user.first_name or user.username}!')
            
            # Redirect based on user type
            next_page = request.GET.get('next', 'dashboard')
            return redirect(next_page)
        else:
            messages.error(request, '❌ Invalid username or password.')
    
    return render(request, 'achievements/login.html')

@login_required
def logout_view(request):
    """Logout user"""
    logout(request)
    messages.success(request, '👋 You have been logged out successfully.')
    return redirect('home')

@login_required
def dashboard(request):
    """Student dashboard - accessible to all authenticated users"""
    # Initialize variables
    student_achievements = []
    profile = None
    approved_count = 0
    form = AchievementForm()
    
    try:
        # Get user achievements and profile
        student_achievements = Achievement.objects.filter(student=request.user).order_by('-created_at')
        profile = getattr(request.user, 'studentprofile', None)
        approved_count = Achievement.objects.filter(student=request.user, is_approved=True).count()
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
    
    # Handle form submission
    if request.method == 'POST':
        form = AchievementForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                achievement = form.save(commit=False)
                achievement.student = request.user
                achievement.save()
                messages.success(request, '🎉 Achievement submitted for approval!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error submitting achievement: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    
    context = {
        'achievements': student_achievements,
        'form': form,
        'profile': profile,
        'approved_count': approved_count
    }
    return render(request, 'achievements/dashboard.html', context)

@login_required
def profile(request):
    """Student profile page - accessible to all authenticated users"""
    try:
        profile = get_object_or_404(StudentProfile, user=request.user)
        total_achievements = Achievement.objects.filter(student=request.user).count()
        approved_achievements = Achievement.objects.filter(student=request.user, is_approved=True).count()
    except Exception as e:
        profile = None
        total_achievements = 0
        approved_achievements = 0
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Profile updated successfully!')
                return redirect('profile')
            except Exception as e:
                messages.error(request, f'❌ Error updating profile: {str(e)}')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile)
    
    context = {
        'profile': profile,
        'form': form,
        'total_achievements': total_achievements,
        'approved_achievements': approved_achievements
    }
    return render(request, 'achievements/profile.html', context)

@login_required
def delete_achievement(request, achievement_id):
    """Delete student's achievement"""
    try:
        achievement = get_object_or_404(Achievement, id=achievement_id, student=request.user)
        achievement.delete()
        messages.success(request, '🗑️ Achievement deleted successfully!')
    except Exception as e:
        messages.error(request, '❌ Error deleting achievement.')
    
    return redirect('dashboard')

@staff_required
def admin_dashboard(request):
    """Staff-only dashboard"""
    try:
        student_count = User.objects.filter(is_staff=False).count()
        staff_count = User.objects.filter(is_staff=True).count()
        achievement_count = Achievement.objects.count()
        pending_approvals = Achievement.objects.filter(is_approved=False).count()
        approved_achievements = Achievement.objects.filter(is_approved=True).count()
    except Exception as e:
        student_count = staff_count = achievement_count = pending_approvals = approved_achievements = 0
    
    context = {
        'student_count': student_count,
        'staff_count': staff_count,
        'achievement_count': achievement_count,
        'pending_approvals': pending_approvals,
        'approved_achievements': approved_achievements,
    }
    return render(request, 'achievements/admin_dashboard.html', context)

@superuser_required
def register_staff(request):
    """Superuser-only staff registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                # Make user staff
                user.is_staff = True
                user.save()
                
                # Update profile to mark as staff
                profile = user.studentprofile
                profile.is_student = False
                profile.save()
                
                messages.success(request, f'✅ Staff member {user.username} created successfully!')
                return redirect('admin_dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error creating staff member: {str(e)}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'achievements/register_staff.html', {'form': form})

def admin_site_permission(request):
    """
    Custom permission check for admin site access
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not request.user.is_staff:
        messages.error(request, "❌ Access denied. Only staff members can access the admin panel.")
        return redirect('home')
    
    # Allow access to admin site
    from django.contrib.admin.sites import site
    return site.index(request)

def contact_submit(request):
    """Handle contact form submission"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            subject = request.POST.get('subject')
            message = request.POST.get('message')
            
            # Save to database
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            
            messages.success(request, '📧 Thank you for your message! We will get back to you soon.')
        except Exception as e:
            messages.error(request, '❌ Error sending message. Please try again.')
    
    return redirect('home')

def get_achievements_api(request):
    """API endpoint for achievements"""
    try:
        achievements = Achievement.objects.filter(is_approved=True).values(
            'id', 'name', 'event', 'prize', 'competition', 'image', 'description'
        )
        return JsonResponse(list(achievements), safe=False)
    except Exception as e:
        return JsonResponse([], safe=False)

# Error handlers
def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)