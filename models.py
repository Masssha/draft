from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator


STATE_CHOICES = (
    ('basket', 'basket state'),
    ('new', 'new'),
    ('confirmed', 'confirmed'),
    ('assembled', 'assembled'),
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('canceled', 'canceled'),
)

USER_TYPE_CHOICES = (
    ('shop', 'shop'),
    ('buyer', 'buyer'),

)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    date_of_birth = models.DateField(verbose_name="Birthday",null=True)
    company = models.CharField(max_length=40, blank=True)
    position = models.CharField(max_length=40, blank=True)
    # username_validator = UnicodeUsernameValidator()
    # username = models.CharField(
    #     _('username'),
    #     max_length=150,
    #     help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
    #     validators=[username_validator],
    #     error_messages={
    #         'unique': _("A user with that username already exists."),
    #     },
    # )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    type = models.CharField(verbose_name='user type', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')
    REQUIRED_FIELDS = ["first_name",]
    USERNAME_FIELD = 'email'
    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = "users"
        ordering = ('email',)


class Shop(models.Model):
    name = models.CharField(max_length=30)
    url = models.URLField(null=True, blank=True)
    state = models.BooleanField(default=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=30)
    shop = models.ManyToManyField(Shop, related_name='categories', blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=30)
    category = models.ForeignKey(Category, related_name='products', blank=True, on_delete=models.CASCADE)
    model = models.CharField(max_length=100)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Parameter(models.Model):
    parameter_name = models.CharField(max_length=30, verbose_name="name of parameter")

    class Meta:
        #this line should be deleded
        verbose_name = 'Product Parameters'
        ordering = ('parameter_name',)

    def __str__(self):
        return self.parameter_name


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, related_name="information")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, blank=True, related_name="information")
    quantity = models.IntegerField()
    price = models.PositiveIntegerField()
    price_rrc = models.PositiveIntegerField(verbose_name="recommended retail price")


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    parameter_value = models.CharField(max_length=100, verbose_name="parameter value")

    def __str__(self):
        return f'{self.product_info} {self.parameter} {self.parameter_value}'


class Contact(models.Model):
    user = models.ForeignKey(Person, related_name='contacts', blank=True, on_delete=models.CASCADE)
    city = models.CharField(max_length=30)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=15)
    structure = models.CharField(max_length=15, blank=True)
    building = models.CharField(max_length=15, blank=True)
    apartment = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f'{self.city} {self.street} {self.house}'

    class Meta:
        verbose_name = 'user contacts'


class Order(models.Model):
    user = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='orders',  blank=True)
    state = models.CharField(choices=STATE_CHOICES, max_length=15)
    order_dt = models.DateTimeField(auto_now_add=True, verbose_name="order date and time")
    contact = models.ForeignKey(Contact, related_name='orders', blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ('-order_dt',)

    def __str__(self):
        #this line should be edited
        return f'{self.order_dt} {self.user}'


class OrderItem(models.Model):
     order = models.ForeignKey(Order, on_delete=models.CASCADE)
     product = models.ForeignKey(Product, on_delete=models.CASCADE)
     quantity = models.PositiveIntegerField()
     shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
     product_info = models.ForeignKey(ProductInfo, related_name='ordered_items', blank=True, on_delete=models.CASCADE)

     class Meta:
         verbose_name = 'item in an order'


class ConfirmEmailToken(models.Model):

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    user = models.ForeignKey(Person, related_name='confirm_email_tokens', on_delete=models.CASCADE, verbose_name=_("The User which is associated to this password reset token"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("When was this token generated"))
    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)
