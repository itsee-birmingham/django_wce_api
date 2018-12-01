"use strict";
var testing;
var api = (function (){

  //Private functions
  var csrfSafeMethod, getEtag, setEtag, getCSRFToken;

  //Private variables
  const etags = {};

  //Public functions
  var setupAjax, createItemInDatabase, updateItemInDatabase, updateFieldsInDatabase,
  getItemFromDatabase, getItemsFromDatabase, deleteItemFromDatabase, deleteM2MItemFromDatabase,
  getCurrentUser;
  //temporary promise public functions will replace non-promise versions eventually
  var createItemInDatabasePromise, updateItemInDatabasePromise, updateFieldsInDatabasePromise,
  getItemFromDatabasePromise, getItemsFromDatabasePromise, deleteItemFromDatabasePromise,
  deleteM2MItemFromDatabasePromise, getCurrentUserPromise;

  csrfSafeMethod = function (method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  };

  getEtag = function (app, model, id) {
    if (etags.hasOwnProperty(app)
          && etags[app].hasOwnProperty(model)
          && etags[app][model].hasOwnProperty(id)) {
      return etags[app][model][id];
    }
    return '*';
  };

  //TODO: think about whether we ever need to clear an etag and if we should also be
  //refusing to save * (these two issues might be related)
  setEtag = function (app, model, id, etag) {
    if (etag !== null && etag !== undefined) {
      if (!etags.hasOwnProperty(app)) {
        etags[app] = {};
      }
      if (!etags[app].hasOwnProperty(model)) {
        etags[app][model] = {};
      }
      etags[app][model][id] = etag;
    }
  };

  getCSRFToken = function () {
    var cookieValue, cookies, cookie;
      cookieValue = null;
      if (document.cookie && document.cookie != '') {
          cookies = document.cookie.split(';');
          for (let i = 0; i < cookies.length; i+=1) {
              cookie = $.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.indexOf('csrftoken=') === 0) {
                  cookieValue = decodeURIComponent(cookie.substring(10));
                  break;
              }
          }
      }
      return cookieValue;
  };

  setupAjax = function () {
    $.ajaxSetup({
      beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
      }
    });
  };


  getCurrentUser = function (success_callback, error_callback) {
    $.ajax({'url': '/api/whoami',
        'method': 'GET'}
    ).done(function (response, textStatus, jqXHR) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      }
    });
    return;
  };

  getCurrentUserPromise = function () {
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/whoami',
          'method': 'GET'}
      ).then(function(response) {
        resolve(response);
      }).catch(function(response){
        reject(response);
      })
    });
  };

  getItemFromDatabase = function (app, model, id, success_callback, error_callback) {
    $.ajax({'url': '/api/' + app + '/' + model + '/' + id,
        'method': 'GET'}
    ).done(function (response, textStatus, jqXHR) {
      setEtag(app, model, id, jqXHR.getResponseHeader('etag'));
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      }
    });
    return;
  };

  getItemFromDatabasePromise = function (app, model, id) {
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/' + app + '/' + model + '/' + id,
          'method': 'GET'}
      ).then(function(response, textStatus, jqXHR) {
        setEtag(app, model, id, jqXHR.getResponseHeader('etag'));
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };

  //TODO: consider whether this should also set etag for all items returned
  //TODO: if no value is given for a search field then everything is returned (limited by any additional search fields)
  //if we are looking for a list of ids and there are none then this gets an empty id value and ideally it would return nothing.
  getItemsFromDatabase = function (app, model, criteria, method, success_callback, error_callback) {
    $.ajax({'url': '/api/' + app + '/' + model,
        'method': method,
        'data': criteria}
    ).done(function (response) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      }
    });
    return;
  };

  //TODO: consider whether this should also set etag for all items returned
  getItemsFromDatabasePromise = function (app, model, criteria, method) {
    if (typeof method === undefined) {
      method = 'GET';
    }
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/' + app + '/' + model,
          'method': method,
          'data': criteria}
      ).then(function(response) {
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };

  createItemInDatabase = function (app, model, data, success_callback, error_callback) {
    delete data['csrfmiddlewaretoken'];
    $.ajax({'url': '/api/' + app + '/' + model + '/create/',
        'headers': {'Content-Type': 'application/json'},
        'dataType': 'json',
        'method': 'POST',
        'data': JSON.stringify(data)}
    ).done(function (response, textStatus, jqXHR) {
      setEtag(app, model, response.id, jqXHR.getResponseHeader('etag'));
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response)
      }
    });
    return;
  };

  createItemInDatabasePromise = function (app, model, data) {
    //TODO: see if we need to delete the csrfmiddleware token - I'm not sure it is there
    //it might be in the form but it might not be needed
    delete data['csrfmiddlewaretoken'];
    return new Promise(function (resolve, reject) {
      //TODO: this might need to return an etag - check rules
      $.ajax({'url': '/api/' + app + '/' + model + '/create/',
          'headers': {'Content-Type': 'application/json'},
          'dataType': 'json',
          'method': 'POST',
          'data': JSON.stringify(data)}
      ).then(function (response, textStatus, jqXHR) {
        setEtag(app, model, response.id, jqXHR.getResponseHeader('etag'));
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };


  updateItemInDatabase = function (app, model, data, success_callback, error_callback) {
    //TODO: see if we need to delete the csrfmiddleware token - I'm not sure it is there
    //it might be in the form but it might not be needed
    delete data['csrfmiddlewaretoken'];
    $.ajax({'url': '/api/' + app + '/' + model + '/update/' + data.id,
        'headers': {'Content-Type': 'application/json'},
        'dataType': 'json',
        'method': 'PUT',
        'data': JSON.stringify(data)}
    ).done(function (response) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      }
    });
    return;
  };

  updateItemInDatabasePromise = function (app, model, data) {
    //TODO: see if we need to delete the csrfmiddleware token - I'm not sure it is there
    //it might be in the form but it might not be needed
    delete data['csrfmiddlewaretoken'];
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/' + app + '/' + model + '/update/' + data.id,
          'headers': {'Content-Type': 'application/json'},
          'dataType': 'json',
          'method': 'PUT',
          'data': JSON.stringify(data)}
      ).then(function (response) {
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };


  updateFieldsInDatabase = function (app, model, id, data, success_callback, error_callback) {
    var etag = getEtag(app, model, id);
    $.ajax({'url': '/api/' + app + '/' + model + '/update/' + id,
        'headers': {'Content-Type': 'application/json', 'If-Match': etag},
        'dataType': 'json',
        'method': 'PATCH',
        'data': JSON.stringify(data)}
    ).done(function (response, textStatus, jqXHR) {
      setEtag(app, model, id, jqXHR.getResponseHeader('etag'));
      if (typeof success_callback !== 'undefined') {
        success_callback(response);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response)
      }
    });
    return;
  };

  updateFieldsInDatabasePromise = function (app, model, id, data) {
    return new Promise(function (resolve, reject) {
      var etag = getEtag(app, model, id);
      $.ajax({'url': '/api/' + app + '/' + model + '/update/' + id,
          'headers': {'Content-Type': 'application/json', 'If-Match': etag},
          'dataType': 'json',
          'method': 'PATCH',
          'data': JSON.stringify(data)}
      ).then(function (response, textStatus, jqXHR) {
        setEtag(app, model, id, jqXHR.getResponseHeader('etag'));
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };

  deleteItemFromDatabase = function (app, model, id, success_callback, error_callback) {
    $.ajax({'url': '/api/' + app + '/' + model + '/delete/' + id,
        'method': 'DELETE'}
    ).done(function (response, textStatus, jqXHR) {
      if (typeof success_callback !== 'undefined') {
        success_callback(response, jqXHR.status);
      }
    }).fail(function (response) {
      if (typeof error_callback !== 'undefined') {
        error_callback(response);
      }
    });
    return;
  };

  deleteItemFromDatabasePromise = function (app, model, id) {
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/' + app + '/' + model + '/delete/' + id,
          'method': 'DELETE'}
      ).then(function (response, textStatus, jqXHR) {
        resolve(jqXHR.status);
      }).catch(function (response) {
        reject(response);
      });
    });
  };


  deleteM2MItemFromDatabase = function (app, model, model_id, fieldname, item_model, item_id, success_callback, error_callback) {
      $.ajax({'url': '/api/' + app + '/' + model + '/' + model_id + '/' + fieldname + '/delete/' + item_model + '/' + item_id,
              'headers': {'Content-Type': 'application/json'}, //'X-CSRFToken': csrf_token,
              'dataType': 'json',
              'method': 'PATCH'
              }
      ).done(function (response) {//{'json': JSON.stringify(data), 'csrfmiddlewaretoken': csrf_token}, 'success': function (response) {
          if (typeof success_callback !== 'undefined') {
              success_callback(response);
          }
      }).fail(function (response) {
          if (typeof error_callback !== 'undefined') {
              error_callback(response)
          }
      });
      return;
  };

  deleteM2MItemFromDatabasePromise = function (app, model, model_id, fieldname, item_model, item_id) {
    return new Promise(function (resolve, reject) {
      $.ajax({'url': '/api/' + app + '/' + model + '/' + model_id + '/' + fieldname + '/delete/' + item_model + '/' + item_id,
              'headers': {'Content-Type': 'application/json'}, //'X-CSRFToken': csrf_token,
              'dataType': 'json',
              'method': 'PATCH'
              }
      ).then(function (response){
        resolve(response);
      }).catch(function (response) {
        reject(response);
      });
    });
  };

  if (testing) {
    return {
      //private
      csrfSafeMethod: csrfSafeMethod,
      getEtag: getEtag,
      setEtag: setEtag,
      //public
      setupAjax: setupAjax,
      createItemInDatabase: createItemInDatabase,
      updateItemInDatabase: updateItemInDatabase,
      updateFieldsInDatabase: updateFieldsInDatabase,
      getItemFromDatabase: getItemFromDatabase,
      getItemsFromDatabase: getItemsFromDatabase,
      deleteItemFromDatabase: deleteItemFromDatabase,
      deleteM2MItemFromDatabase: deleteM2MItemFromDatabase,
      createItemInDatabasePromise: createItemInDatabasePromise,
      updateItemInDatabasePromise: updateItemInDatabasePromise,
      updateFieldsInDatabasePromise: updateFieldsInDatabasePromise,
      getItemFromDatabasePromise: getItemFromDatabasePromise,
      getItemsFromDatabasePromise: getItemsFromDatabasePromise,
      deleteItemFromDatabasePromise: deleteItemFromDatabasePromise,
      deleteM2MItemFromDatabasePromise: deleteM2MItemFromDatabasePromise,
      getCurrentUserPromise: getCurrentUserPromise,
      getCurrentUser: getCurrentUser
    }
  } else {
    return {
      setupAjax: setupAjax,
      createItemInDatabase: createItemInDatabase,
      updateItemInDatabase: updateItemInDatabase,
      updateFieldsInDatabase: updateFieldsInDatabase,
      getItemFromDatabase: getItemFromDatabase,
      getItemsFromDatabase: getItemsFromDatabase,
      deleteItemFromDatabase: deleteItemFromDatabase,
      deleteM2MItemFromDatabase: deleteM2MItemFromDatabase,
      createItemInDatabasePromise: createItemInDatabasePromise,
      updateItemInDatabasePromise: updateItemInDatabasePromise,
      updateFieldsInDatabasePromise: updateFieldsInDatabasePromise,
      getItemFromDatabasePromise: getItemFromDatabasePromise,
      getItemsFromDatabasePromise: getItemsFromDatabasePromise,
      deleteItemFromDatabasePromise: deleteItemFromDatabasePromise,
      deleteM2MItemFromDatabasePromise: deleteM2MItemFromDatabasePromise,
      getCurrentUserPromise: getCurrentUserPromise,
      getCurrentUser: getCurrentUser,
      getCSRFToken: getCSRFToken

    }
  }


} () );
