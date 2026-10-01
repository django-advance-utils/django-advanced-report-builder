/*
 * Load a saved query into jQuery QueryBuilder without losing it to one rule it cannot show.
 *
 * QueryBuilder refuses a whole rule set when any rule names a filter it does not offer (a renamed or
 * removed field) or an operator that filter no longer allows; the editor then shows nothing, and saving
 * from there wipes every rule. split() sets aside only those rules, drops any group they leave empty
 * (QueryBuilder rejects an empty group, which would wipe the query just the same), and lists what it set
 * aside so warn() can say so.
 */
window.arbQueryRules = (function ($) {
    'use strict';

    function split(group, filters, dropped) {
        if (!group || !Array.isArray(group.rules)) {
            return group;
        }
        var byId = {};
        filters.forEach(function (filter) {
            byId[filter.id] = filter;
        });

        function walk(node) {
            node.rules = node.rules.filter(function (rule) {
                if (rule && Array.isArray(rule.rules)) {
                    walk(rule);
                    return rule.rules.length > 0;
                }
                if (!rule || rule.empty || rule.id === undefined || rule.id === null) {
                    return true;  // a placeholder rule QueryBuilder fills in itself
                }
                var filter = byId[rule.id];
                if (filter === undefined) {
                    dropped.push(String(rule.id));
                    return false;
                }
                if (rule.operator && Array.isArray(filter.operators) && filter.operators.indexOf(rule.operator) === -1) {
                    dropped.push(String(rule.id) + ' ' + rule.operator);
                    return false;
                }
                return true;
            });
        }

        walk(group);
        return group;
    }

    function warn($builder, warningId, dropped) {
        var $warning = $('#' + warningId);
        var unique = dropped.filter(function (value, index) {
            return dropped.indexOf(value) === index;
        });
        if (unique.length === 0) {
            $warning.remove();
            return;
        }
        if ($warning.length === 0) {
            $warning = $('<div class="alert alert-warning col-12"></div>').attr('id', warningId);
            $builder.before($warning);
        }
        var one = unique.length === 1;
        $warning.text(
            unique.length + (one ? ' rule refers' : ' rules refer') +
            ' to a field or operator that is no longer available (' + unique.join(', ') + ') and ' +
            (one ? 'is' : 'are') + ' not shown. Saving this query will remove ' + (one ? 'it.' : 'them.')
        );
    }

    return {split: split, warn: warn};
}(jQuery));
