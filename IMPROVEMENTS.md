# Q-Explorer Improvements

## Completed Tasks
- ✅ Limited all music lists (albums, singles, songs, artists) to maximum 6 items with "See All" buttons linking to full pages.
- ✅ Added new routes: `/see-all/<type>` for search results and `/artist/<id>/discography/<category>` for artist discography.
- ✅ Switched all UI text to English (buttons, labels, messages).
- ✅ Cleaned up Russian comments in `app.py` for consistency.

## 1. UX / Interface
- ✅ Add pagination or "Load more" on `/see-all/<type>` and `/artist/<id>/discography/<category>`.
- ✅ Add search autocomplete or suggestions to help users find artists/albums faster.
- ✅ Show skeleton loaders or loading states while API requests are in progress.
- ✅ Add sorting/filtering options for albums and singles (e.g. release date, year, popularity).

## 2. Performance
- ✅ Cache API results from iTunes, Deezer, and Last.fm to reduce repeated requests.
- ✅ Cache artist and album images if possible to speed up repeated views.
- ✅ Use lazy loading for all cards and images, not only artists.

## 3. Code Architecture
- ✅ Refactor `app.py` into separate modules or Flask blueprints: search, artist, album, api, auth.
- ✅ Move configuration out of `app.py` into `config.py` and use environment variables consistently.
- ✅ Reduce duplicate search logic between `index()` and `see_all()` by extracting shared helper functions.
- ✅ Make `sort_albums` more flexible and robust for EPs, live albums, compilations, and duplicates.

## 4. Functionality
- Add separate pages for "All Albums" and "All Singles" per artist with filters.
- Add "See all similar artists" and "See more top songs" on the artist page.
- Add preview/play support or direct sample links from album or track cards.

## 5. Testing and Stability
- Add unit tests for `/see-all/...`, `/artist/<id>/discography/...`, `artist_page`, `album_page`.
- Add template rendering tests to ensure `See All` buttons and section limits appear correctly.

## 6. Accessibility
- Add `alt` attributes to all images.
- Add `aria-label` for buttons like like/favorite, playlist add, and "See All".
- Ensure keyboard navigation works across cards, modals, and buttons.

## 7. Miscellaneous
- ✅ Keep visible UI text in English if the site is English-only.
- ✅ Clean up Russian comments in code for consistency.

## Suggested Priorities
1. Cache APIs and add pagination for large result pages.
2. Refactor `app.py` into blueprints and separate config.
3. Add search autocomplete and sorting options.
4. Improve loading states and accessibility.
