# -*- coding: utf-8 -*-
from datetime import timedelta

from django import forms
from django.contrib.auth.models import User

from tcms.core.utils import string_to_list
from tcms.core.forms.fields import UserField
from tcms.management.models import Product, Version, Build, EnvGroup
from tcms.testplans.models import TestPlan
from tcms.testcases.models import TestCase
from .models import TestRun, TestCaseRunStatus


class BaseRunForm(forms.Form):
    summary = forms.CharField(max_length=255)
    manager = UserField()
    default_tester = UserField(required=False)
    estimated_time = forms.DurationField(required=False)
    build = forms.ModelChoiceField(
        queryset=Build.objects.none(),
    )
    notes = forms.CharField(
        widget=forms.Textarea,
        required=False,
    )

    def populate(self, product_id):
        query = {'product_id': product_id}
        self.fields['build'].queryset = Build.list_active(query)

    def clean_estimated_time(self):
        estimated_time = self.cleaned_data.get('estimated_time', timedelta(0))
        # can be either None, '', 0 or timedelta(0)
        if not estimated_time:
            estimated_time = timedelta(0)
        return estimated_time


class NewRunForm(BaseRunForm):
    case = forms.ModelMultipleChoiceField(
        label='Cases',
        queryset=TestCase.objects.filter(case_status__id=2).all(),
    )


class XMLRPCNewRunForm(BaseRunForm):
    plan = forms.ModelChoiceField(
        queryset=TestPlan.objects.none(),
    )

    def assign_plan(self, plan_id):
        self.fields['plan'].queryset = TestPlan.objects.filter(pk=plan_id)
        self.populate(self.fields['plan'].queryset.first().product_id)


class XMLRPCUpdateRunForm(XMLRPCNewRunForm):
    plan = forms.ModelChoiceField(
        label='Test Plan',
        queryset=TestPlan.objects.all(),
        required=False,
    )
    summary = forms.CharField(
        label='Summary',
        required=False
    )
    manager = forms.ModelChoiceField(
        label='Manager', queryset=User.objects.all(), required=False
    )
    product = forms.ModelChoiceField(
        label='Product',
        queryset=Product.objects.all(),
        empty_label=None, required=False
    )
    product_version = forms.ModelChoiceField(
        label='Product Version',
        queryset=Version.objects.none(),
        empty_label=None, required=False
    )
    build = forms.ModelChoiceField(
        label='Build',
        queryset=Build.objects.all(),
        required=False
    )

    def clean_status(self):
        return self.cleaned_data.get('status')


# =========== Forms for search/filter ==============

class SearchRunForm(forms.Form):
    """
        Includes *only* fields used in search.html b/c
        the actual search is now done via JSON RPC.
    """
    plan = forms.CharField(required=False)
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False
    )
    product_version = forms.ModelChoiceField(
        queryset=Version.objects.none(),
        required=False
    )
    build = forms.ModelChoiceField(
        label='Build',
        queryset=Build.objects.none(),
        required=False,
    )
    default_tester = UserField(required=False)
    tag__name__in = forms.CharField(required=False)
    env_group = forms.ModelChoiceField(
        queryset=EnvGroup.get_active().all(),
        required=False
    )

    def clean_tag__name__in(self):
        return string_to_list(self.cleaned_data['tag__name__in'])

    def populate(self, product_id=None):
        if product_id:
            self.fields['product_version'].queryset = Version.objects.filter(
                product__pk=product_id
            )
            self.fields['build'].queryset = Build.objects.filter(
                product__pk=product_id
            )


# ===========================================================================
# Case run form
# ===========================================================================


class BaseCaseRunForm(forms.Form):
    build = forms.ModelChoiceField(
        label='Build', queryset=Build.objects.all(),
    )
    case_run_status = forms.ModelChoiceField(
        label='Case Run Status', queryset=TestCaseRunStatus.objects.all(),
        required=False,
    )
    assignee = UserField(label='Assignee', required=False)
    case_text_version = forms.IntegerField(
        label='Case text version', required=False
    )
    notes = forms.CharField(label='Notes', required=False)
    sortkey = forms.IntegerField(label='Sortkey', required=False)


# =========== Forms for XML-RPC functions ==============

class XMLRPCNewCaseRunForm(BaseCaseRunForm):
    assignee = forms.ModelChoiceField(
        label='Assignee', queryset=User.objects.all(), required=False
    )
    run = forms.ModelChoiceField(
        label='Test Run', queryset=TestRun.objects.all(),
    )
    case = forms.ModelChoiceField(
        label='TestCase', queryset=TestCase.objects.all(),
    )

    def clean_assignee(self):
        data = self.cleaned_data.get('assignee')
        if not data:
            if self.cleaned_data.get('case') \
                    and self.cleaned_data['case'].default_tester_id:
                data = self.cleaned_data['case'].default_tester
            elif self.cleaned_data.get('run') \
                    and self.cleaned_data['run'].default_tester_id:
                data = self.cleaned_data['run'].default_tester

        return data

    def clean_case_text_version(self):
        data = self.cleaned_data.get('case_text_version')
        if not data and self.cleaned_data.get('case'):
            tc_ltxt = self.cleaned_data['case'].latest_text()
            if tc_ltxt:
                data = tc_ltxt.case_text_version

        return data

    def clean_case_run_status(self):
        data = self.cleaned_data.get('case_run_status')
        if not data:
            data = TestCaseRunStatus.objects.get(name='IDLE')

        return data


class XMLRPCUpdateCaseRunForm(BaseCaseRunForm):
    assignee = forms.ModelChoiceField(
        label='Assignee', queryset=User.objects.all(), required=False
    )
    build = forms.ModelChoiceField(
        label='Build', queryset=Build.objects.all(), required=False,
    )
