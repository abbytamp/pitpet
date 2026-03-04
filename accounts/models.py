from django.db import models

class UserManager(models.Manager):
    def get_by_natural_key(self, username):
        return self.get(username=username)

class User(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        STAFF = 'staff', 'Staff'
        GROOMER = 'groomer', 'Groomer'
        MANAGER = 'manager', 'Manager'
        SUPERADMIN = 'superadmin', 'Superadmin'

    username = models.CharField(max_length=255, unique=True) # Email login
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.username} ({self.role})"

    # Password management (plain text)
    def set_password(self, raw_password):
        self.password = raw_password

    def check_password(self, raw_password):
        return self.password == raw_password

    # Auth System compatibility properties
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return self.role in [self.Role.STAFF, self.Role.MANAGER, self.Role.SUPERADMIN]

    @property
    def is_superuser(self):
        return self.role in [self.Role.MANAGER, self.Role.SUPERADMIN]

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    @property
    def pk(self):
        return self.id

class Groomer(models.Model):
    class ServiceType(models.TextChoices):
        HOME = 'home', 'Home'
        CLINIC = 'clinic', 'Clinic'
        
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'groomer'}, related_name='groomer_profile')
    service_type = models.CharField(max_length=10, choices=ServiceType.choices)

    def __str__(self):
        return f"{self.user.full_name} - {self.service_type}"

