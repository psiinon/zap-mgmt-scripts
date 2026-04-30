var DIR = "/zap/wrk/";
var NAME = "Escaped XSS";
var TARGET = "escape";
var RULES = [40012, 40026, 200002, 200007, 210000, 220000];
var MIN_LEVEL = 2;
var IGNORE_PATHS = ['/serverside/encodeUrl/a', '/serverside/escapeHtml/a'];
var BROKEN_PATHS = [
	'/serverside/encodeUrl/attribute_name',
	'/serverside/encodeUrl/attribute_quoted',
	'/serverside/encodeUrl/attribute_script',
	'/serverside/encodeUrl/attribute_singlequoted',
	'/serverside/encodeUrl/attribute_unquoted',
	'/serverside/encodeUrl/body',
	'/serverside/encodeUrl/body_comment',
	'/serverside/encodeUrl/css_import',
	'/serverside/encodeUrl/css_style_font_value',
	'/serverside/encodeUrl/css_style_value',
	'/serverside/encodeUrl/head',
	'/serverside/encodeUrl/href',
	'/serverside/encodeUrl/js_assignment',
	'/serverside/encodeUrl/js_comment',
	'/serverside/encodeUrl/js_eval',
	'/serverside/encodeUrl/js_quoted_string',
	'/serverside/encodeUrl/js_singlequoted_string',
	'/serverside/encodeUrl/js_slashquoted_string',
	'/serverside/encodeUrl/tagname',
	'/serverside/encodeUrl/textarea',
	'/serverside/escapeHtml/attribute_quoted',
	'/serverside/escapeHtml/body',
	'/serverside/escapeHtml/body_comment',
	'/serverside/escapeHtml/css_style',
	'/serverside/escapeHtml/css_style_value',
	'/serverside/escapeHtml/head',
	'/serverside/escapeHtml/href',
	'/serverside/escapeHtml/js_assignment',
	'/serverside/escapeHtml/textarea',
];
