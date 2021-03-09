var expect  = require('chai').expect;
var request = require('request');

it('Main page content', function(done) {
    request('http://app:3000' , function(error, response, body) {
        expect(body).to.equal('Health OK!');
        done();
    });
});