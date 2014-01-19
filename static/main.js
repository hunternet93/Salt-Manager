var settings;

function list_minions(data, status) {
    var minion_template = Handlebars.compile( $('#minion-template').html() );
    $('#minionlist').empty();
    for (m in data.minions) {
        minion = data.minions[m];
        minion.quickactions = settings.quickactions;
        $('#minionlist').append( minion_template(minion) );
    }

    //$('#minionlist').collapsibleset('refresh');
    $('#minionlist').trigger('create');
}

function list_keys(data, status) {
    var key_template = Handlebars.compile( $('#keys-template').html() );
    $('#keys-unaccepted').empty();
    $('#keys-accepted').empty();
    for (m in data.minions_unaccepted) {
        minion = data.minions_unaccepted[m];
        $('#keys-unaccepted').append( key_template(minion) );
    }

    for (m in data.minions) {
        minion = data.minions[m];
        $('#keys-accepted').append( key_template(minion) );
    }
    
    $('#keys-unaccepted').trigger('create');
    $('#keys-accepted').trigger('create');
}

function run_command(tgt, fun, arg) { $.post('/ajax/runcommand', {'tgt': tgt, 'fun': fun, 'arg': JSON.stringify(arg)}, command_dialog); }

function command_dialog(data, status) {
    if (typeof data.error != 'undefined') {
        $('#error-dialog-message').empty();
        $('#error-dialog-message').text(data.error);
        $.mobile.changePage('#error-dialog', { role: 'dialog' } );
    }

    if (typeof data.result != 'undefined') {
        $('#command-dialog-result').empty();
        $('#command-dialog-result').text(data.result);    
        $.mobile.changePage('#command-dialog', { role: 'dialog' } ); 
    }
}

function load_settings(data, status) { settings = data; }

$(document).ready(function() {
    $.get('/ajax/settings', load_settings);
    $(document).on("pageinit", "#minions", function() { $.get("/ajax/listminions", list_minions); } );
    $(document).on("pageinit", "#keys", function() { $.get("/ajax/listkeys", list_keys); } );

});
