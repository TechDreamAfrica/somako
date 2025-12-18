from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import subscription_views
from . import notification_views

app_name = 'accounts'

urlpatterns = [
    path('signup/services/', views.signup_services_view, name='signup_services'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    path('profile/pwa/', views.pwa_profile_view, name='pwa_profile'),
    path('profile/pwa/edit/', views.pwa_profile_edit_view, name='pwa_profile_edit'),
    path('profile/pwa/password/', views.pwa_profile_password_view, name='pwa_profile_password'),
    path('profile/pwa/settings/', views.pwa_profile_settings_view, name='pwa_profile_settings'),
    path('profile/pwa/orders/', views.pwa_profile_orders_view, name='pwa_profile_orders'),
    path('profile/pwa/saved/', views.pwa_profile_saved_view, name='pwa_profile_saved'),
    path('profile/<str:username>/', views.public_profile_view, name='public_profile'),
    path('profiles/browse/', views.browse_profiles_view, name='browse_profiles'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Role Application URLs
    path('roles/apply/', views.apply_for_role, name='apply_for_role'),
    path('roles/my-applications/', views.my_role_applications, name='my_role_applications'),
    path('roles/dashboard-redirect/', views.role_dashboard_redirect, name='role_dashboard_redirect'),

    # Subscription URLs
    path('subscription/plans/', subscription_views.subscription_plans, name='subscription_plans'),
    path('subscription/subscribe/<int:plan_id>/', subscription_views.subscribe, name='subscribe'),
    path('subscription/verify/<str:reference>/', subscription_views.subscription_verify, name='subscription_verify'),
    path('subscription/manage/', subscription_views.subscription_manage, name='subscription_manage'),
    path('subscription/cancel/', subscription_views.subscription_cancel, name='subscription_cancel'),
    path('subscription/renew/', subscription_views.subscription_renew, name='subscription_renew'),
    path('subscription/webhook/', subscription_views.paystack_webhook, name='paystack_webhook'),

    # Notification URLs
    path('notifications/', notification_views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/read/', notification_views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', notification_views.mark_all_read, name='mark_all_read'),
    path('notifications/preferences/', notification_views.notification_preferences, name='notification_preferences'),
    path('api/notifications/unread-count/', notification_views.get_unread_count, name='unread_count'),

    # Password reset URLs (Traditional link-based)
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # OTP Password reset URLs (Main website)
    path('password_reset/otp/', views.OTPPasswordResetView.as_view(), name='otp_password_reset'),
    path('password_reset/otp/verify/', views.OTPPasswordResetVerifyView.as_view(), name='otp_password_reset_verify'),
    path('password_reset/otp/new-password/', views.OTPPasswordResetNewPasswordView.as_view(), name='otp_password_reset_new_password'),
    path('password_reset/otp/done/', views.OTPPasswordResetDoneView.as_view(), name='otp_password_reset_done'),
    path('change_password/', auth_views.PasswordChangeView.as_view(template_name='accounts/change_password.html', success_url='/accounts/profile/'), name='change_password'),

    # PWA-specific authentication URLs
    path('login/pwa/', views.pwa_login_view, name='pwa_login'),
    path('logout/pwa/', views.pwa_logout_view, name='pwa_logout'),
    path('signup/pwa/', views.pwa_signup_view, name='pwa_signup'),
    path('verify/pwa/', views.pwa_verify_view, name='pwa_verify'),
    path('verify/pwa/resend/', views.pwa_resend_verification_code, name='pwa_resend_verification'),

    # PWA Password reset URLs (OTP-based)
    path('password_reset/pwa/', views.PWAPasswordResetView.as_view(), name='pwa_password_reset'),
    path('password_reset/pwa/verify/', views.PWAPasswordResetVerifyView.as_view(), name='pwa_password_reset_verify'),
    path('password_reset/pwa/new-password/', views.PWAPasswordResetNewPasswordView.as_view(), name='pwa_password_reset_new_password'),
    path('password_reset/pwa/done/', views.PWAPasswordResetDoneView.as_view(), name='pwa_password_reset_done'),
    path('reset/pwa/<uidb64>/<token>/', views.PWAPasswordResetConfirmView.as_view(), name='pwa_password_reset_confirm'),
    path('reset/pwa/done/', views.PWAPasswordResetCompleteView.as_view(), name='pwa_password_reset_complete'),
]
