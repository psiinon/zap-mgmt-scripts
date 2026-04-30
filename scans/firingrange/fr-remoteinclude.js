var DIR = "/zap/wrk/";
var NAME = "Remote Inclusion XSS";
var TARGET = "remoteinclude";
var RULES = [40012, 40026, 200002, 200007, 210000, 220000];
var MIN_LEVEL = 1;
var IGNORE_PATHS = ['/', '/script_hash.html#https:/google.com'];
var BROKEN_PATHS = [];
