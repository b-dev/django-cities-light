# -*- coding: utf-8 -*-

import re
import autoslug
import pytz

from django.utils.encoding import python_2_unicode_compatible

from django.db import models
from django.db.models import lookups
from django.utils.encoding import force_text
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from unidecode import unidecode

from .validators import timezone_validator
from .settings import INDEX_SEARCH_NAMES, CITIES_LIGHT_APP_NAME

from general.constants import STATE_TYPES
from general.managers import TranslateEntityManager, CustomEntityManager
from general.fields import CustomTranslatedFields
from hvad.models import TranslatableModel

__all__ = ['AbstractCountry', 'AbstractRegion', 'AbstractCity',
           'CONTINENT_CHOICES']


CONTINENT_CHOICES = (
    ('OC', _('Oceania')),
    ('EU', _('Europe')),
    ('AF', _('Africa')),
    ('NA', _('North America')),
    ('AN', _('Antarctica')),
    ('SA', _('South America')),
    ('AS', _('Asia')),
)

ALPHA_REGEXP = re.compile('[\W_]+', re.UNICODE)


def to_ascii(value):
    """
    Convert a unicode value to ASCII-only unicode string.

    For example, 'République Françaisen' would become 'Republique Francaisen'
    """
    return force_text(unidecode(value))


def to_search(value):
    """
    Convert a string value into a string that is usable against
    City.search_names.

    For example, 'Paris Texas' would become 'paristexas'.
    """

    return ALPHA_REGEXP.sub('', to_ascii(value)).lower()


@python_2_unicode_compatible
class Base(models.Model):
    """
    Base model with boilerplate for all models.
    """

    name_ascii = models.CharField(max_length=200, blank=True, db_index=True)
    slug = autoslug.AutoSlugField(populate_from='name_ascii')
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    alternate_names = models.TextField(null=True, blank=True, default='')

    state = models.SmallIntegerField(verbose_name=_('Publish state'), choices=STATE_TYPES, default=1)
    default_language = models.CharField(max_length=2, choices=settings.LANGUAGES, default='en', verbose_name=_('Default language'))

    class Meta:
        abstract = True
        # ordering = ['name']

    def __str__(self):
        display_name = getattr(self, 'display_name', None)
        if display_name:
            return display_name
        return self.name


class AbstractCountry(Base, TranslatableModel):
    """
    Base Country model.
    """

    translations = CustomTranslatedFields(
        name=models.CharField(
            max_length=200
        ),
        source_language=models.CharField(
            max_length=2,
            choices=settings.LANGUAGES,
            default='en',
            verbose_name=_('Source language')
        ),
        is_auto_translated=models.BooleanField(
            verbose_name=_('Auto Translated'),
            default=False
        ),
        meta={'unique_together': [('name', 'language_code', 'master')]},
    )

    code2 = models.CharField(max_length=2, null=True, blank=True, unique=True)
    code3 = models.CharField(max_length=3, null=True, blank=True, unique=True)
    continent = models.CharField(max_length=2, db_index=True,
                                 choices=CONTINENT_CHOICES)
    tld = models.CharField(max_length=5, blank=True, db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    allow_translate = models.BooleanField(verbose_name=_('Allow Translate'), default=True)

    objects = CustomEntityManager()
    published = TranslateEntityManager()

    class Meta(Base.Meta):
        verbose_name_plural = _('countries')
        abstract = True
        ordering = ['name']

    @property
    def name_(self):
        return self.name

    def __str__(self):
        return self.name


class AbstractRegion(Base, TranslatableModel):
    """
    Base Region/State model.
    """

    translations = CustomTranslatedFields(
        name=models.CharField(
            max_length=200
        ),
        display_name=models.CharField(
            max_length=200
        ),
        source_language=models.CharField(
            max_length=2,
            choices=settings.LANGUAGES,
            default='en',
            verbose_name=_('Source language')
        ),
        is_auto_translated=models.BooleanField(
            verbose_name=_('Auto Translated'),
            default=False
        ),
        meta={'unique_together': [('name', 'language_code', 'master')]},
    )

    geoname_code = models.CharField(max_length=50, null=True, blank=True,
                                    db_index=True)

    country = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Country',
                                on_delete=models.CASCADE)

    allow_translate = models.BooleanField(verbose_name=_('Allow Translate'), default=True)

    objects = CustomEntityManager()
    published = TranslateEntityManager()

    class Meta(Base.Meta):
        unique_together = (('country', 'slug'))
        verbose_name = _('region/state')
        verbose_name_plural = _('regions/states')
        abstract = True
        ordering = ['name']

    @property
    def name_(self):
        return self.name

    def get_display_name(self):
        return '%s, %s' % (self.name, self.country.name)


class ToSearchIContainsLookup(lookups.IContains):
    """IContains lookup for ToSearchTextField."""

    def get_prep_lookup(self):
        """Return the value passed through to_search()."""
        value = super(ToSearchIContainsLookup, self).get_prep_lookup()
        return to_search(value)


class ToSearchTextField(models.TextField):
    """
    Trivial TextField subclass that passes values through to_search
    automatically.
    """


ToSearchTextField.register_lookup(ToSearchIContainsLookup)


class AbstractCity(Base, TranslatableModel):
    """
    Base City model.
    """

    translations = CustomTranslatedFields(
        name=models.CharField(
            max_length=200,
            db_index=True
        ),
        display_name=models.CharField(
            max_length=200
        ),
        source_language=models.CharField(
            max_length=2,
            choices=settings.LANGUAGES,
            default='en',
            verbose_name=_('Source language')
        ),
        is_auto_translated=models.BooleanField(
            verbose_name=_('Auto Translated'),
            default=False
        ),
        meta={'unique_together': [('name', 'language_code', 'master')]},
    )

    search_names = ToSearchTextField(
        max_length=4000,
        db_index=INDEX_SEARCH_NAMES,
        blank=True,
        default='')

    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    longitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    region = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Region', blank=True,
                               null=True, on_delete=models.CASCADE)
    country = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Country',
                                on_delete=models.CASCADE)
    population = models.BigIntegerField(null=True, blank=True, db_index=True)
    feature_code = models.CharField(max_length=10, null=True, blank=True,
                                    db_index=True)
    timezone = models.CharField(max_length=40, blank=True, null=True,
                                db_index=True, validators=[timezone_validator])

    allow_translate = models.BooleanField(verbose_name=_('Allow Translate'), default=True)

    objects = CustomEntityManager()
    published = TranslateEntityManager()

    class Meta(Base.Meta):
        unique_together = (('region', 'slug'))
        verbose_name_plural = _('cities')
        abstract = True
        ordering = ['name']

    @property
    def name_(self):
        return self.name

    def get_display_name(self):
        if self.region_id:
            try:
                return '%s, %s, %s' % (self.name, self.region.name,
                                   self.country.name)
            except:
                return '%s, %s' % (self.name, self.country.name)

        else:
            return '%s, %s' % (self.name, self.country.name)

    def get_timezone_info(self):
        """Return timezone info for self.timezone.

        If self.timezone has wrong value, it returns timezone info
        for value specified in settings.TIME_ZONE.
        """
        try:
            return pytz.timezone(self.timezone)
        except (pytz.UnknownTimeZoneError, AttributeError):
            return pytz.timezone(settings.TIME_ZONE)
