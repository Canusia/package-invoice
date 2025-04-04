

window.refreshTable = function () {
    var selectedRows = table.rows({ selected: true });

    selectedRows.deselect();

    table.ajax.reload(null, false);
    tbl_record_notes.ajax.reload(null, false);
};

function do_action(action, id) {

    let data = {
        'action': action,
        'ids': Array()
    }
    data.ids.push(id)

    url = record_bulk_action;
    let modal = "modal-bulk_actions"

    $.ajax({
        type: "GET",
        url: url,
        data: data,
        success: function(response) {
            $("#bulk_modal_content").html(response);
            $("#" + modal).modal('show');
        }
    });
}



$('form.frm_ajax').submit(function(event) {

    var blocked_element = $(this).parent()
    $(blocked_element).block();
    event.preventDefault()

    form = $(this)

    if($("input, select, textarea").hasClass('is-invalid'))
        $("input, select, textarea").removeClass('is-invalid')
    
    if($("input, select, textarea").next('p').length) 
        $("input, select, textarea").nextAll('p').empty();

    let action = $(form).attr('action')
    let first_element = '';
    
    $.post({
        url: action,
        data: $(form).serialize(),
        error: function(xhr, status, error) {

            let errors = $.parseJSON(xhr.responseJSON.errors);
            
            for (var name in errors) {
                for (var i in errors[name]) {
                    var $input = $("[name='"+ name +"']");
                    $input.addClass('is-invalid');

                    $input.after("<p class='invalid-feedback'><strong class=''>" + errors[name][i].message + "</strong></p>");
                }

                if(first_element == '')
                    $input.focus()
                else {
                    first_element = '-'
                }
            }

            var span = document.createElement('span')
            span.innerHTML = xhr.responseJSON.message
            swal({
                title: xhr.responseJSON.message,
                content: span,
                icon: 'warning'
            });

            $(blocked_element).unblock();
        },
        success: function(response) {
            swal({
                title: 'Success',
                text: response.message,
                icon: response.status
            }).then(
                (value) => {
                    if(response.action == 'reload')
                        location.reload();
                }
            )
            $(blocked_element).unblock();
        }
    })
    return false
});

jQuery(document).ready(function($) {
    $("input.delete").on("click", function() {
        if(!confirm("Are you sure you want to permanently delete this record and all associated data?"))
            return;
        
            $.ajax({
            type: 'GET',
            url: record_delete_url,
            success: function (response) {
                $.unblockUI();
                swal({
                    title: 'Success',
                    text: response.message,
                    icon: response.status
                }).then(
                    (value) => {
                        if(window.frameElement !== null) {
                            window.parent.closeModal()
                        } else {
                            window.location = "{% url 'invoice:all' %}";
                        }
                    }
                )
            }
        });
    });
    
    $("input.clone").on("click", function() {
        if(!confirm("Are you sure you want to clone this invoice and all associated data?"))
            return;
        
        $.ajax({
            type: 'GET',
            url: record_clone_url,
            success: function (response) {
                $.unblockUI();
                swal({
                    title: 'Success',
                    text: response.message,
                    icon: response.status
                }).then(
                    (value) => {
                        if(window.frameElement !== null) {
                            window.parent.closeModal()
                        } else {
                            window.location = response.redirect_url
                        }
                    }
                )
            }
        });
    });


    $(document).on("click", "form.filter #id_btn_filter", function () {
        load_data();
    })

    function load_data() {
        let form = $('form.filter')
        let newURL = baseURL + '&' + $(form).serialize();

        table.ajax.url(newURL).load()
    }

    table = $('#records_all')
        .DataTable({
            initComplete: function () {
                this.api()
                    .columns()
                    .every(function () {
                        let column = this;
                        let title = column.footer().textContent;
        
                        // Create input element
                        if(title != '') {
                            let input = document.createElement('input');
                            input.className = 'form-control'
                            input.placeholder = "Search " + title;

                            column.footer().replaceChildren(input);
            
                            // Event listener for user input
                            input
                            .addEventListener('keyup', $.debounce(1500,() => {
                                if (column.search() !== this.value) {
                                    column.search(input.value).draw();
                                }
                            }));
                        }
                    });


                // Restore state
                var state = this.api().state.loaded();
                if (state) {
                    this.api().columns().eq(0).each(function (colIdx) {
                        var colSearch = state.columns[colIdx].search;

                        if (colSearch.search) {
                            $('input', this.column(colIdx).footer()).val(colSearch.search);
                        }
                    });
                }
            },
            searchDelay: 1500,
            columnDefs: [
                {
                    orderable: false,
                    className: 'select-checkbox',
                    targets: 0
                }
            ],
            select: {
                style: 'os',
                selector: 'td:first-child'
            },
            rowId: 'id',
            dom: 'B<"float-left mt-3 mb-3"l><"float-right mt-3"f><"row clear">rt<"row"<"col-6"i><"col-6 float-right"p>>',
            buttons: [
                {
                    extend: 'csv', className: 'btn btn-sm btn-primary text-white text-light',
                    text: '<i class="fas fa-file-csv text-white"></i>&nbsp;CSV',
                    titleAttr: 'Export Records in current View to CSV' 
                },
                { 
                    extend: 'print', className: 'btn btn-sm btn-primary text-white text-light',
                    text: '<i class="fas fa-print text-white"></i>&nbsp;Print',
                    titleAttr: 'Print Records in Current View' 
                },
                {
                    className: 'btn btn-sm btn-primary text-white text-light',
                    text: '<i class="fas fa-plus text-white"></i>&nbsp;Add New Item',
                    titleAttr: 'Add New Item',
                    action: function ( e, dt, node, config ) {
                        do_action('add_new_item', record_id);
                    }
                },
            ],
            'orderCellsTop': true,
            'fixedHeader': true,
            // searching: false,
            ajax: baseURL,
            serverSide: true,
            processing: true,
            order: [[1, 'asc']],
            // stateSave: true,
            language: {
                'loadingRecords': '&nbsp;',
            },
            'lengthMenu': [30, 50, 100],

            'columns': [
                {
                    'searchable': false,
                    'orderable': false,
                    'render': function (data, type, row, meta) {
                        return ''
                    }
                },
                null,
                null,
                {
                  'render': function (data, type, row, meta) {
                        if(row.formatted_amount == '$0.00') {
                            return " ";
                        }
                        return row.formatted_amount
                    }  
                },

                {
                    'searchable': false,
                    'orderable': false,
                    'render': function (data, type, row, meta) {
                        return "<a class='btn btn-sm btn-primary' onClick=\"do_action('edit_line_item', '" + row.id + "')\" href='#'>Edit/View Details</a>"
                    }
                }
            ]
        }
    );


});


jQuery(document).ready(function($) {

    tbl_record_notes = $('#record_notes').DataTable({
        dom: 'B<"float-left mt-3 mb-3"l><"float-right mt-3"f><"row clear">rt<"row"<"col-6"i><"col-6 float-right"p>>',
        buttons: [
        {
            extend: 'csv', className: 'btn btn-sm btn-primary text-white text-light',
            text: '<i class="fas fa-file-csv text-white"></i>&nbsp;CSV',
            titleAttr: 'Export results to CSV'
            },
            {
            extend: 'print', className: 'btn btn-sm btn-primary text-white text-light',
            text: '<i class="fas fa-print text-white"></i>&nbsp;Print',
            titleAttr: 'Print'
            },
            ],
            'lengthMenu': [30, 50, 100],
            'order': [[0, 'desc']],
            'columns': [
            {
            'searchable': false,
            },
            {
            'render': function (data, type, row, meta) {
                let note = row.note            
                return note
            }
            },
            
            {
            'render': function (data, type, row, meta) {
                return row.createdby.last_name + ", " +
                row.createdby.first_name
            }
            },
            {
            'orderable': false,
            'searchable': false,
            'render': function (data, type, row, meta) {
                return '';
                return '<a href="#notes" data-id="' + row.id + '" class="delete_student_note btn btn-sm btn-danger"><i class="fa fa-trash"></i></a>';
            }
        }
        ]
    }
    );
    });
