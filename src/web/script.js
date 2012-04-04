//Global variables for latitude and longitude of the client
//This is helpful when the user types in 'here' as a value of
//a new property.
var latitude,longitude;

//These are shortcuts that users can type to enter special things
var typeOptions = ['null', 'true', 'false', 'here', 'now'];

//This is a handy way of passing events inside the application
var dispatcher = _.clone(Backbone.Events);

var DO_APP_CONTENT_CHANGE_EVENT = 'app:set';
var DID_APP_CONTENT_CHANGE_EVENT = 'app:change';

//Our model couldn't be simpler. The only thing we need done is to keep
//the intrinsic Model id property in sync with the '__id' property.
//This is necessary for actions like destroy which won't be called unless
//an id is set
ModelEntity = Backbone.Model.extend({});

EntityCollection = Backbone.Collection.extend({type:null, model:ModelEntity});

//This is the main widget of our application
EntityWidget = Backbone.View.extend({
	initialize:function(options){
		this.el.innerHTML = $('#entity-body').html();

		//Create a default entity to start
		this.setModel(new ModelEntity());
		//Set the typeahead so the user is aware of some of the options
		//available to him
		this.$('#new-value').typeahead({source: typeOptions});
	},
	setModel:function(newModel){
		this.model = newModel;
		//We listen to the change and destroy backbone events on
		//the model
		this.model.on('change', function(){this.render();}, this);
		this.model.on('destroy', function(){/*TODO: Do something!*/},this);
		this.render();
	},
	//This is a div HTML element at its core
	tagName:'div',
	//These are the important events this widget handles
	events: {
	//This creates a new property in our model object when the 
	//'add' button is pressed	
	"click .add-property":function(){
		this.add();
	},
	//This saves the object to the server when the save button
	//is pressed
	"click .save":function(){
		this.model.save();
	}, 
	//This fetches the object with the given '__id' property
	//effectivly syncing our client-side model with what the server has
	"click .retrieve":function(){
		this.model.fetch();
	},
	//This will destroy the object on the server that has the given
	//'__id'. The client-side object should stick around though in
	//case we change our mind
	"click .delete":function(){
		this.model.destroy();
	},
	//This will add the property when 'enter' is pressed
	"keypress #new-value":function(event){
		if (event.which == 13)
		{
			this.add();
		}
	},
	//This is called when the autocomplete box is pressed
	"change #new-value":function(event){
		this.check(event.target.value);
	},
	//This is called every time a character is pressed on keyboard
	"input #new-value":function(event){
		this.check(event.target.value);		
	}},
	//This does some cool stuff to format the value string so that
	//the user knows they are entering an appropriately formatted 
	//property
	check:function(currentText){
		//TODO: Add a part that will allow for shortcutting reference objects
		for (var anOption in typeOptions)
		{
			if (currentText == typeOptions[anOption])
			{
				this.$('#value-control').addClass("success");
				this.$('#value-control').find('.help-inline').html('-> ' + typeOptions[anOption]);
				return;
			}			
		}
		
		//Check for numbers too
		if(/^\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> int');
		}
		else if(/^\d*\.\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> float');
		}
		else if(/^\w+:\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> reference');
		}
		else
		{
			//If there is no match, remove formatting
			this.$('#value-control').removeClass("success");
			this.$('#value-control').find('.help-inline').html('');	
		}		
	},
	add:function()
	{
		//Parse the type as appropriate and then set the model
		result = this.$('#new-value').val();
		if (result=="null")
			result = null;
		else if(result=="true")
			result = true;
		else if(result =="false")
			result = false;		
		else if(result=="here")
		{
			result = latitude.toString()+ "," + longitude.toString();
		}
		else if(result=="now")
		{
			result = new Date().toISOString();
		}
		else if(/^\d+$/.test(result))
		{
			result = parseInt(result, 10);		
		}
		else if(/^\d*\.\d+$/.test(result))
		{
			result = parseFloat(result);      
		}
		else 
		{
			var match = /^(\w+):(\d+)$/.exec(result);
			if(match)
			{
				result = {__type:match[1],__id:parseInt(match[2], 10),__ref:true};				
			}
		}

		this.model.set(this.$('#new-key').val(), result);
	},
	//Rendering takes a template and creates the guts of widget.
	render: function(){
		this.$('#prop-list').empty();
		for (var property in this.model.attributes)
		{
			var newRow = $(document.createElement('tr'));
			var newName = $(document.createElement('td'));
			newName.html(property);
			newRow.append(newName);
			var newVal = $(document.createElement('td'));
			var propVal = this.model.attributes[property];
			if (propVal instanceof Object)
			{
				newVal.html(JSON.stringify(propVal));
			}
			else
			{
				newVal.html(propVal);
			}
			newRow.append(newVal);
			this.$('#prop-list').append(newRow);
		}
		
		var controlForm = this.$('#entity-control');
		var saveButton = $(document.createElement('button')).attr("type","button").addClass("btn btn-primary save").html("Save");
		controlForm.html(saveButton);
		
		if (this.model.id)
		{
			var deleteButton = $(document.createElement('button')).attr("type","button").addClass("btn btn-danger delete").html("Delete");
			controlForm.append(deleteButton);
			var retrieveButton = $(document.createElement('button')).attr("type","button").addClass("btn btn-warning retrieve").html("Retrieve");
			controlForm.append(retrieveButton);
		}
	}
});

//This is the main widget of our application
ExplorerWidget = Backbone.View.extend({
	initialize:function(options){
		//Add the widget to the body.
		$('#main-content').html(this.currentMainView.el);
		
		dispatcher.on(DO_APP_CONTENT_CHANGE_EVENT,function(newModel){
			this.addIfNotPresent(newModel);
			this.render();
			
			//Create the widget that manages the model
			this.currentMainView.setModel(newModel);
			
			dispatcher.trigger(DID_APP_CONTENT_CHANGE_EVENT, newModel);
		}, this);
		this.render();
	},
	currentMainView: new EntityWidget(),
	collections: {},
	tagName:'div',
	className:'well',
	events:{"keypress #search-text":function(event){
		if (event.which == 13)
		{
			this.performSearch();
		}
	},
	'click #search-button':function(){
		this.performSearch();
	}},
	performSearch:function(){
		var searchBoxContents = this.$('#search-text').val();
		if(searchBoxContents.length === 0)
		{
			$.ajax({url:"/api", success:_.bind(function(data, textStatus, jqXHR){
				this.createCollections(data);
			},this)});			
		}
		if (/^\w+$/.test(searchBoxContents))
		{
			$.ajax({url:"/api/" + searchBoxContents, success:_.bind(function(data, textStatus, jqXHR){
				this.createCollections(data);
			},this)});
		}
		else 
		{
			var match = /^(\w+):(\d+)$/.exec(searchBoxContents);
			if(match)
			{
				$.ajax({url:"/api/" + match[1] + "/" + match[2], success:_.bind(function(data, textStatus, jqXHR){
					this.createCollections([data]);
					dispatcher.trigger(DO_APP_CONTENT_CHANGE_EVENT, this.collections[data.__type].at(0));
				},this)});							
			}
		}
	},
	addIfNotPresent:function(model)
	{
		var objectType = model.attributes.__type;
		existingCollection = this.collections[objectType];
		if (existingCollection)
		{
			for(var i = 0; i < existingCollection.length;i++)
			{
				var candidate = existingCollection.at(i);
				if (_.isEqual(candidate.attributes,model.attributes))
				{
					return;
				}
			}
		}
		else
		{
			existingCollection = new EntityCollection();
			existingCollection.type = objectType;
			this.collections[objectType] = existingCollection; 
		}
		existingCollection.add(model);
	},
	createCollections:function(data){
		//Need to reset this every time we create the collections
		this.collections = {};
		for (var item in data)
		{
			var obj = data[item];
			var newEntity = new ModelEntity(obj);
			newEntity.id = obj.__id;
			this.addIfNotPresent(newEntity);
		}
		this.render();
		if (this.currentMainView)
		{
			dispatcher.trigger(DID_APP_CONTENT_CHANGE_EVENT, this.currentMainView.model);
		}		
	},
	allEntityWidgets:[],
	cleanupOldEntityWidgets:function(){
		for (var item in this.allEntityWidgets)
		{
			this.allEntityWidgets[item].cleanup();
		}
	},
	//Rendering takes a template and creates the guts of widget.
	render: function(){
		this.$el.html($('#sidebar-template').html());
		this.cleanupOldEntityWidgets();

		for (var item in this.collections)
		{
			var collection = this.collections[item];
			var newList = $(document.createElement('ul')).addClass('nav nav-list');
			var title = $(document.createElement('li')).addClass('nav-header');
			title.html(collection.type);
			newList.append(title);
				
			for (var i = 0; i < collection.length; i++){
					var newWidget = new EntitySidebarWidget({model:collection.at(i)});
					this.allEntityWidgets.push(newWidget);
					newList.append(newWidget.el);
			}
			this.$el.append(newList);
		}
		
		//This is a confusing way to count the number of elements in 
		//an object
		if (Object.keys(this.collections).length === 0)
		{
			this.$el.append($('#alert-template').html());
		}

		this.$el.append(new NewEntityWidget().el);		
	}
});

EntitySidebarWidget = Backbone.View.extend({
	initialize:function(options){
		this.model.on('change:__id',function(){
			this.render();
		}, this);
		dispatcher.on(DID_APP_CONTENT_CHANGE_EVENT,function(newModel){
			if (_.isEqual(this.model.attributes,newModel.attributes))
			{
				this.$el.addClass("active");
			}
			else
			{
				this.$el.removeClass("active");
			}
		}, this);

		this.render();
	},
	tagName:'li',
	cleanup:function(){
		dispatcher.off(null, null, this);
		this.model.off(null, null, this);
	},
	events:{
		"click a":function(){
			dispatcher.trigger(DO_APP_CONTENT_CHANGE_EVENT, this.model);
			}
	},
	render: function(){
		var inside = document.createElement('a');
		inside.innerHTML = this.model.attributes.__id;
		this.$el.html(inside);
	}
});

NewEntityWidget = Backbone.View.extend({
	initialize:function(options){
		this.render();
	},
	tagName:'div',
	events:{
		"keypress input":function(event){
			if (event.which == 13)
			{
				this.addNew();
			}
		},
		"click a":function(){
			this.addNew();
	}},
	addNew: function(){
		var newObj = new ModelEntity({__type:this.$("input").val()});
		dispatcher.trigger(DO_APP_CONTENT_CHANGE_EVENT, newObj);
	},
	render: function(){
		this.$el.html($('#new-entity-template').html());
	}
});

//The sync class is what backbone uses to sync to the server. It 
//uses a weird method, so I'm doing all the $.ajax calls manually.
Backbone.sync = function(method, model) {
	//We treat update and create calls the same since we overwrite 
	//server values each time.
	//TODO: Error conditions are currently not handled. We need to fix
	//this.
	if (method == "create" || method=="update")
	{
		//Creates the post request and then sets the id on success.
		var asJSON = JSON.stringify(model);
		$.ajax({type:"POST",contentType:"application/json", data:asJSON,url:'/api',success:function(data, textStatus, jqXHR){
			model.id = parseInt(data, 10);
			model.set("__id",model.id);
		}});
	}
	else if (method=="delete")
	{
		//Creates the delete request
		$.ajax({type:"DELETE",url:'/api/'+model.get('__type')+'/'+model.get('__id')});
	}
	else
	{
		//Creates the get request and populates all fields upon success
		$.ajax({url:'/api/'+model.get('__type')+'/'+model.get('__id'), success:function(data, textStatus, jqXHR){
			//This will make sure that properties are also un-set as appropriate
			model.clear({silent: true});
			model.set(data);
			model.id = data.__id;
			}
		});
	}
};

//JQuery to english: 'When the page is done loading, perform this function'
$(function(){
	//Find our current location. This will not work on all browsers,
	//so we should do more checking here eventually.
	navigator.geolocation.getCurrentPosition(function (position) {
		latitude = position.coords.latitude;
		longitude = position.coords.longitude;
	});
	
	//Create the sidebar
	var parentView = new ExplorerWidget();
	
	//Add the widget to the body.
	$('#side-content').append(parentView.el);		
});