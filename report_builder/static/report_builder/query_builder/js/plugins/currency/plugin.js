$.fn.queryBuilder.define('currency', function (options) {

    this.on('getRuleInput.filter', function (h, rule, name) {
        var filter = rule.filter;
        if (filter.template_tag && filter.template_tag === 'internal_currency') {
            h.value = '<div class="input-group" style="padding: 0; margin: 0"> <span class="input-group-addon">' + h.builder.settings.currency_symbol + '</span> <input type="number" step="0.01" onchange="this.value = Number(this.value).toFixed(2);" class="form-control" autocomplete="off" name="' + name + '"> </div>';
        }
    });

    this.on('ruleToJson.filter', function (e, rule) {
        // Save
        var filter = rule.filter;
        if (filter.template_tag && filter.template_tag === 'internal_currency') {
            e.value.value = parseFloat(e.value.value) * 100.0;
        }
    });

    this.on('jsonToRule.filter', function (e, json) {
        // Load
        var filter = e.value.filter;

        if (filter.template_tag && filter.template_tag === 'internal_currency') {
            if (json.value !== undefined) {
                var value = parseFloat(json.value) / 100.0;

                e.value.value = value
            }
        }
    });
});
