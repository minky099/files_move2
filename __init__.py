from .plugin import blueprint, menu, plugin_load, plugin_unload, plugin_info

#from .plugin import blueprint, menu, plugin_load, plugin_unload
#from .plugin import P
#blueprint = P.blueprint
#menu = P.menu
#plugin_load = P.logic.plugin_load
#plugin_unload = P.logic.plugin_unload
#plugin_info = P.plugin_info

try:
    from guessit import guessit
except:
    try:
        os.system("{} install guessit".format(app.config['config']['pip']))
        from guessit import guessit
    except:
        pass
