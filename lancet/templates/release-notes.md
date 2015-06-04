Release {{ version.name }}

# Changelog for version {{ version.name }}
{% for grouper, issues in issues|groupby('fields.issuetype.name') %}
## {{ grouper }}
{%- for issue in issues %}
* [{{ issue.key }}]({{ issue.permalink() }}): {{ issue.fields.summary }}
{%- endfor %}
{% endfor %}
