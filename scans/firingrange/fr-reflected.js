var DIR = "/zap/wrk/";
var NAME = "Reflected XSS";
var TARGET = "reflected";
var RULES = [40012, 40026, 200002, 200007, 210000, 220000];
var MIN_LEVEL = 2;
var IGNORE_PATHS = ['/parameter/form', '/url/a'];
var BROKEN_PATHS = [];
