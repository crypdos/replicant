# Replicant

Discordbot that replicates other users by creating similar messages based on their message history, along with copying their username and avatarpicture. 

### Requires
```
Python >= 3.5
Motor
discord.py rewrite branch
markovify
```

### Usage
Rename ```default-config.ini``` to ```config.ini```  
Enter required fields in config.ini (token, one scrapeserver, one botserver) then run ``python3 bot.py``  
Make sure mongodb is running.  
Before the bot is able to immitate messages, the database has to be created first. To do this use the ```?scrape``` command in a discordchannel that the bot is listening to.  
