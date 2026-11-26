import test from 'node:test';import assert from 'node:assert/strict';import {days,observations} from '../web/model.mjs';
test('discrete source units and absent values',()=>{assert.equal(days('3 weeks'),21);assert.equal(days('1 day'),1);assert.equal(days('No processing time available'),null);assert.equal(days(null),null);});
test('preserves missing country row rather than zero',()=>{assert.equal(observations([null],[{issued:{},observed:'2021-01-20T00:00:00Z',evidence:'source'}],'work')[0].label,'No row in this capture');});
