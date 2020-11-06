// Transcrypt'ed from Python, 2020-04-11 13:41:53
var time = {};
import {AssertionError, AttributeError, BaseException, DeprecationWarning, Exception, IndexError, IterableError, KeyError, NotImplementedError, RuntimeWarning, StopIteration, UserWarning, ValueError, Warning, __JsIterator__, __PyIterator__, __Terminal__, __add__, __and__, __call__, __class__, __envir__, __eq__, __floordiv__, __ge__, __get__, __getcm__, __getitem__, __getslice__, __getsm__, __gt__, __i__, __iadd__, __iand__, __idiv__, __ijsmod__, __ilshift__, __imatmul__, __imod__, __imul__, __in__, __init__, __ior__, __ipow__, __irshift__, __isub__, __ixor__, __jsUsePyNext__, __jsmod__, __k__, __kwargtrans__, __le__, __lshift__, __lt__, __matmul__, __mergefields__, __mergekwargtrans__, __mod__, __mul__, __ne__, __neg__, __nest__, __or__, __pow__, __pragma__, __proxy__, __pyUseJsNext__, __rshift__, __setitem__, __setproperty__, __setslice__, __sort__, __specialattrib__, __sub__, __super__, __t__, __terminal__, __truediv__, __withblock__, __xor__, abs, all, any, assert, bool, bytearray, bytes, callable, chr, copy, deepcopy, delattr, dict, dir, divmod, enumerate, filter, float, getattr, hasattr, input, int, isinstance, issubclass, len, list, map, max, min, object, ord, pow, print, property, py_TypeError, py_iter, py_metatype, py_next, py_reversed, py_typeof, range, repr, round, set, setattr, sorted, str, sum, tuple, zip} from './org.transcrypt.__runtime__.js';
import * as __module_time__ from './time.js';
__nest__ (time, '', __module_time__);
var __name__ = '__main__';
export var TestCase =  __class__ ('TestCase', [object], {
	__module__: __name__,
	get __init__ () {return __get__ (this, function (self, prop) {
		self.stuff = 'much_stuff';
		self.prop = prop;
	});},
	get tryy () {return __get__ (this, function (self) {
		console.log (self.stuff);
	});}
});
export var test = function () {
	var start = time.time ();
	console.log (start);
	var d = dict ({});
	for (var i = 0; i < 1000000; i++) {
		d [i] = TestCase (i);
	}
	console.log (time.time () - start);
	return len (d);
};
export var changeColors = function () {
	var $divs = $ ('div');
	for (var div of $divs) {
		var rgb = (function () {
			var __accu0__ = [];
			for (var i = 0; i < 3; i++) {
				__accu0__.append (int (256 * Math.random ()));
			}
			return __accu0__;
		}) ();
		$ (div).css (dict ([['color', 'rgb({},{},{})'.format (...rgb)]]));
	}
};
export var start = function () {
	window.setInterval (changeColors, 500);
};

//# sourceMappingURL=jquery_demo.map