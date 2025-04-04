MyCE - Invoice
====================
- Setup
In settings.py, 
    add the app to INSTALLED_APPS as 
        'invoice.apps.InvoiceConfig'

    Add path to STATIC_FILES_DIRS
        os.path.join(get_package_path("invoice"), 'staticfiles'),

In myce.urls.py
- path('ce/invoices/', include('invoice.urls.ce'))

In Settings -> Menu add the menu items
{
    "type":"nav-item",
    "icon":"fas fa-fw fa-dollar-sign",
    "label":"Invoices",
    "name":"invoice",
    "sub_menu":[
        {
        "label":"All Invoices",
        "name":"all",
        "url":"invoice:all"
        },
        {
        "label":"PDF Templates",
        "name":"templates",
        "url":"invoice:invoice_templates"
        }
    ]
},

Include debounce in header-includes.html

<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-throttle-debounce/1.1/jquery.ba-throttle-debounce.min.js" integrity="sha512-JZSo0h5TONFYmyLMqp8k4oPhuo6yNk9mHM+FY50aBjpypfofqtEWsAgRDQm94ImLCzSaHeqNvYuD9382CEn2zw==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>

In cis.models.section
- create cost field in ClassSection MOdel
    cost = models.FloatField(default=0)
++++++
In templates/sections/index.html
{
    className: 'btn btn-sm btn-primary text-white text-light',
    text: '<i class="fas fa-edit text-white"></i>&nbsp;Update Class Tuition',
    titleAttr: 'change_tuition',
    action: function ( e, dt, node, config ) {
        do_bulk_action('change_tuition', dt)
    }
},
In cis.vews.section
++++++
    if action == 'change_tuition':
        return change_tuition(request)
++++++
def change_tuition(request):
    template = 'cis/sections/bulk_action.html'

    if request.method == 'POST':

        form = BulkClassTutionChangeForm(data=request.POST)

        if form.is_valid():
            status = form.save(request)

            data = {
                'status':'success',
                'message':'Successfully updated records',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    form = BulkClassTutionChangeForm(ids)
    context = {
        'title': 'Change Section Tuition',
        'form': form,
        'status': 'display'
    }
    
    return render(request, template, context)
    

In cis.forms.term
- enable cost per credit hour field for AcademicYear Model

class BulkClassTutionChangeForm(forms.Form):
    record_ids = forms.MultipleChoiceField(
        required=False,
        label='Records to Update',
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )
    
    new_cost_per_section = forms.FloatField(
        required=True,
        label='New Cost Per Section'
    )
    
    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='change_tuition'
    )

    def __init__(self, record_ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if record_ids:
            records = ClassSection.objects.filter(
                id__in=record_ids
            )

            record_choices = []
            for record in records:
                record_choices.append(
                    (
                        record.id,
                        f"{record} / ${record.cost}"
                    )
                )
                
            self.fields['record_ids'].choices = record_choices
            self.fields['record_ids'].initial = record_ids
        else:
            record_choices = []
            for record_id in kwargs.get('data').getlist('record_ids'):
                record_choices.append(
                    (record_id, record_id)
                )

            self.fields['record_ids'].choices = record_choices
            self.fields['record_ids'].required = False

    def save(self, request=None):
        data = self.cleaned_data
        
        records = ClassSection.objects.filter(
            id__in=data.get('record_ids')
        )

        # skip initiating signal
        records.update(
            cost=data.get('new_cost_per_section')
        )

        for record in records:
            note_message = f'Updated cost to {record.cost}'
            record.add_note(request.user, note_message)

        return records