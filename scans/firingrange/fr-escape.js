var DIR = "/zap/wrk/";
var NAME = "Escaped XSS";
var TARGET = "escape";
var RULES = [40012, 40026, 200002, 200007, 210000, 220000];
var MIN_LEVEL = 2;
var IGNORE_PATHS = ['/serverside/encodeUrl/a', '/serverside/escapeHtml/a'];
var BROKEN_PATHS = ['/serverside/escapeHtml/body'];
