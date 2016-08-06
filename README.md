# yugioh-dor-deckedit
A python tool for editing the deck data in Yu-Gi-Oh Duelist of Roses for the PS2

Currently is only known to support the US version. For J/EU version it might be 
necessary to modify the STARTER_DECK_OFFSET and CPU_DECK_OFFSET values.

Choose the deck you want to modify on the left. On the right are the cards for the deck.
The leader card has, in addition to its card ID, also a rank that can be modified that
goes from 0 to 15. Both leader ID and rank are at the top. 
Below are the card IDs for the remaining 40 cards in the deck.

For the card ID you can either type in the numeric value, or a part of the card name.
The tool will attempt to autocomplete the card name, but will tell you if there are
too many cards matching your name.
