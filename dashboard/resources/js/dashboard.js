//Global variables for latitude and longitude of the client
//This is helpful when the user types in 'here' as a value of
//a new property.
var latitude,longitude;

//These are shortcuts that users can type to enter special things
var typeOptions = ['null', 'true', 'false', 'here', 'now', 'file'];

//This is a handy way of passing events inside the application
var dispatcher = _.clone(Backbone.Events);

var DO_APP_CONTENT_CHANGE_EVENT = 'app:set';
var DID_APP_CONTENT_CHANGE_EVENT = 'app:change';

//Our model couldn't be simpler.
ModelEntity = Backbone.Model.extend({});

//Our collection model is pretty damn simple too. We add the 'type' property 
//so that we can group collections by Model class type (user, entry, etc)
EntityCollection = Backbone.Collection.extend({type:null, model:ModelEntity});

//This is the main widget of our application
EntityWidget = Backbone.View.extend({
	initialize:function(options){
		//Create the scaffold of the widget (other bits and pieces are 
		//plugged in in render())
		this.el.innerHTML = $('#entity-body').html();
		
		//Renders the object initially 
		this.render();

		//Set the typeahead so the user is aware of the options
		//available to him
		this.$('#new-value').typeahead({source: typeOptions});
	},
	//This is a convenience method for parents to set the model.
	//We attach ourselves to this object so we listen to events.
	setModel:function(newModel){
		//detach from last model object
		if (this.model)
		{
			this.model.off(null, null, this);	
		}
		
		this.model = newModel;
		//We listen to the change and destroy backbone events on
		//the model
		this.model.on('change', function(){this.render();}, this);
		this.model.on('destroy', _.bind(function(){this.$el.prepend($('#delete-alert-template').html());
},this));
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
	//effectively synchronizing our client-side model with what the server has
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
		//Go through the keywords list. These elements are
		//immediately converted into something different.
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
		//And our references to objects using the special syntax:
		//<type>:<id>
		else if(/^\w+:\d+$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> reference');
		}
		//This allows for dictionaries. Any nesting is not supported
		else if(/^\{("\w+"\:[^,]+(,"\w+"\:[^,]+)*)?\}$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> dictionary');
		}
		else if(/^\[([^,\[\]]+(,[^,\[\]]+)*)?\]$/.test(currentText))
		{
			this.$('#value-control').addClass("success");
			this.$('#value-control').find('.help-inline').html('-> array');			
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
		else if(result=="file")
		{
			new FilePicker({destField:this.$('#new-value')}).$el.modal('show');
			//Don't actually add something to the main... the 
			//modal will do this.
			return;
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
			//Check and convert references to other objects
			var match = /^(\w+):(\d+)$/.exec(result);
			if(match)
			{
								
			}
			else
			{
				match = /(^\{.*\}$)|(^\[.*\]$)/.exec(result);
				if (match){
					result = JSON.parse(result);
				}				
			}
		}

		this.model.set(this.$('#new-key').val(), result);
	},
	//Rendering takes a template and creates the guts of widget.
	render: function(){
		if (this.model)
		{
			this.$('#add-prop-button').removeClass('disabled');
			this.$('input').removeClass('disabled').prop('disabled',false);

			//Empty all current elements
			this.$('#prop-list').empty();
			
			//Go through all current properties and add a line for each.
			for (var property in this.model.attributes)
			{
				var newRow = $(document.createElement('tr'));
				var newName = $(document.createElement('td'));
				newName.html(property);
				newRow.append(newName);
				var newVal = $(document.createElement('td'));
				var propVal = this.model.attributes[property];
				
				if (/^\/[^\/]+\/[^\/]+$/.test(propVal))
				{
					newVal.html('<iframe src="' + propVal + '"></iframe>');
				}
				else
				{
					newVal.html(JSON.stringify(propVal));
				}
				newRow.append(newVal);
				this.$('#prop-list').append(newRow);
			}
			
			//Get the bottom form which will change according to 
			//whether or not this is an entity that exists in the database
			var controlForm = this.$('#entity-control');
			var saveButton = $(document.createElement('button')).prop("type","button").addClass("btn btn-primary save").html("Save");
			controlForm.html(saveButton);
			
			if (this.model.id)
			{
				var deleteButton = $(document.createElement('button')).prop("type","button").addClass("btn btn-danger delete").html("Delete");
				controlForm.append(' ');
				controlForm.append(deleteButton);
				var retrieveButton = $(document.createElement('button')).prop("type","button").addClass("btn btn-warning retrieve").html("Retrieve");
				controlForm.append(' ');
				controlForm.append(retrieveButton);
			}
		}
		else
		{
			this.$('#add-prop-button').addClass('disabled');
			this.$('input').addClass('disabled').prop('disabled',true);
		}
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

//This is the main widget of our application
ExplorerWidget = Backbone.View.extend({
	initialize:function(options){
		//Add the widget to the body.
		$('#main-content').html(this.currentMainView.el);
		this.$el.html($('#sidebar-template').html());
		this.$('#new-entity-sidebar').html(new NewEntityWidget().el);
		
		//Register to listen to the add content event.
		dispatcher.on(DO_APP_CONTENT_CHANGE_EVENT,function(newModel){
			this.addIfNotPresent(newModel);
			this.render();
			
			//Create the widget that manages the model
			this.currentMainView.setModel(newModel);
			
			dispatcher.trigger(DID_APP_CONTENT_CHANGE_EVENT, newModel);
		}, this);
		this.render();
	},
	//Creates the default widget of the page and maintains a link to
	//it. This is because we need a way to determine which model is 
	//currently displayed
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
	//This is what is called when the search button is pressed
	performSearch:function(){
		//The current text in the search box
		var searchBoxContents = this.$('#search-text').val();
		
		var targetURL = '/api' + searchBoxContents;
		//Call create collections to create the lists of different objects
		$.ajax({url:targetURL, success:_.bind(function(data, textStatus, jqXHR){
			this.createCollections(data);
		},this)});			
	},
	addIfNotPresent:function(model)
	{
		//This goes through existing groups and checks to see if
		//the model that is added is already present in the list.
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
		//But we need to go through all of them to make sure that all
		//listeners are removed from them.
		for(var oldCollection in this.collections)
		{
			var aCollection = this.collections[oldCollection];
			for (var i = 0; i<  aCollection.length; i++)
			{
				aCollection.at(i).off();
			}
			this.collections[oldCollection].off();
		}
		//Clear the existing collections
		this.collections = {};
		for (var item in data)
		{
			var obj = data[item];
			var newEntity = new ModelEntity(obj);
			newEntity.id = obj.__id;
			this.addIfNotPresent(newEntity);
		}
		//Render it now
		this.render();
		if (this.currentMainView.model)
		{
			//Now that we have added a bunch of new ones, let's see
			//if the list contains what we have already.
			dispatcher.trigger(DO_APP_CONTENT_CHANGE_EVENT, this.currentMainView.model);
		}		
	},
	//Keeps a list of all child widgets because we need to clear them
	//out each time.
	allEntityWidgets:[],
	//Does house-cleaning so we don't have zombie objects
	cleanupOldEntityWidgets:function(){
		for (var item in this.allEntityWidgets)
		{
			this.allEntityWidgets[item].cleanup();
		}
	},
	//Rendering takes a template and creates the guts of widget.
	render: function(){
		this.cleanupOldEntityWidgets();

		this.$("#sidebar-list").empty();
		for (var item in this.collections)
		{
			var collection = this.collections[item];
			var title = $(document.createElement('li')).addClass('nav-header');
			title.html(collection.type);
			this.$("#sidebar-list").append(title);
				
			for (var i = 0; i < collection.length; i++){
					var newWidget = new EntitySidebarWidget({model:collection.at(i)});
					this.allEntityWidgets.push(newWidget);
					this.$("#sidebar-list").append(newWidget.el);
			}
		}
		
		//This is the only way to see how many keys exist for this
		//object
		if (Object.keys(this.collections).length === 0)
		{
			this.$('#sidebar-list').append($('#alert-template').html());
		}
	}
});

//This is the small version of what you see in the main content
//area. It shows the ID of the object and shows whether the main
//content is displayed
EntitySidebarWidget = Backbone.View.extend({
	initialize:function(options){
		this.model.on('change:__id',function(){
			//Every time the __id changes, we need to update this
			this.render();
		}, this);
		//This is required because this entity is created on the 'DO'
		//event and then the DID is called for the object we are 
		//currently selected
		dispatcher.on(DID_APP_CONTENT_CHANGE_EVENT,function(newModel){
			//This listens for an event that the selected item has changed
			//and then updates based on that
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
		//Clean up our dependencies
		dispatcher.off(null, null, this);
		this.model.off(null, null, this);
	},
	events:{
		"click a":function(){
			dispatcher.trigger(DO_APP_CONTENT_CHANGE_EVENT, this.model);
			}
	},
	render: function(){
		//Create the guts
		var inside = document.createElement('a');
		inside.innerHTML = this.model.attributes.__id;
		this.$el.html(inside);
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
		$.ajax({type:"DELETE",url:'/api/'+model.get('__type')+'/'+model.get('__id')		});
	}
	else
	{
		//Creates the get request and populates all fields upon success
		$.ajax({url:'/api/'+model.get('__type')+'/'+model.get('__id'), success:function(data, textStatus, jqXHR){
			//This will make sure that properties are also un-set as appropriate
			model.clear({silent: true});
			model.set(data[0]);
			model.id = data[0].__id;
			}
		});
	}
};

FilePicker = Backbone.View.extend({
	//This is the constructor of the view. From other tutorials, 
	//it's common shorthand just to render the view.
	initialize: function(){
		this.destField = this.options.destField;
		$.ajax('/prepare_upload',{success:_.bind(function(data){
			this.$('.uploader').fileupload({
				dropZone: this.$el,
				autoUpload: true,
				url:data,
				paramName:'soundbyte',
				done: _.bind(function (e, data) {
					this.destField.val(data.result);
					this.$el.modal('hide');
				}, this)
			});
		},this)});
		this.render();
	},
	//These two attributes define the type of HTML element this
	//view is
	destField:null,
	tagName: 'div',
	className: 'modal fade',
	events:{
		'click button': function()
		{
			this.$el.modal('hide');
		}
	},
	//This defines what happens when this view is rendered.
	render: function(){
		//This takes a template from our HTML file and creates 
		//The modal HTML from this markup
		this.el.innerHTML = $('#modal-body-template').html();
	}
});

//JQuery to english: 'When the page is done loading, perform this function'
$(function(){
	//Create the sidebar
	var parentView = new ExplorerWidget();
	
	//Add the widget to the body.
	$('#side-content').append(parentView.el);		
});