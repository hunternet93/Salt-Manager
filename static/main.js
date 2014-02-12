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

function list_modules(data, status) {
    var modules_template = Handlebars.compile( $('#modules-template').html() );
    $('#moduleslist').html(modules_template(data));
    $('#moduleslist').listview('refresh');
}

function run_command(tgt, fun, arg) { $.post('/ajax/runcommand', {'tgt': tgt, 'fun': fun, 'arg': JSON.stringify(arg)}) }

function load_settings(data, status) { settings = data; }

$(document).ready(function() {
    $.get('/ajax/settings', load_settings);
    $(document).on("pageinit", "#minions", function() { $.get("/ajax/listminions", list_minions); } );
    $(document).on("pageinit", "#keys", function() { $.get("/ajax/listkeys", list_keys); } );
    $(document).on("pageinit", "#modules", function() { $.get("/ajax/listmodules", list_modules); } );
    

});
