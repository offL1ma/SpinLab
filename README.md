# SpinLab

This project is licensed under the Microsoft Reference Source License.
You may view and read the code for reference only.
Any copying, forking, modification, redistribution, or commercial use is strictly prohibited without prior written permission.

The project is a initiative to create a music platform for a final-couse project. The platform has the objective to 

SpinLab is a web application for buying and selling music-related items—such as vinyl records, CDs, cassettes, MP3s, and more. Any visitor can browse listings and use search filters without logging in; however, clicking on a listing redirects them to the login or signup page.

Once authenticated, users can view item details, message sellers, and save listings to favorites. Hovering over a listing owned by another user displays only a “favorite” button—if it belongs to the logged-in user, “edit” and “delete” options also appear.

The homepage header displays the SpinLab logo on the left and buttons on the right for accessing favorites, personal profile, and creating new listings. In the user profile area, users can update their name, email, and password, and even delete their account—automatically removing all their listings.

An administrator panel provides full CRUD capabilities for managing users and listings, along with the ability to grant or revoke admin privileges.

Listings can be filtered by price (ascending/descending), category, artist/band, and release year. The submission form for new listings requires fields such as name, price (formatted automatically in euros), release year, artist/band, category (rock | pop, indie | alternative, jazz | blues, hip hop, Brazilian, Portuguese, industrial | experimental, metal | hard rock, soul | funk | disco), format (LP, CD, cassette, MP3, etc.), dimensions (automatically converted to centimeters), and allows uploading up to five images.

The listings page displays up to 20 results per page, with navigation to load more. Listings can be marked as “available” or “sold”—once marked sold, they are removed from public view but remain accessible in the seller's authenticated history.
