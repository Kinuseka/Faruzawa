const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');
const pagination = document.getElementById('pagination');
const loading = document.getElementById('loading'); 
var isSearching = false;
var prevTerm = '';

searchBtn.addEventListener('click', () => {
    return searchEvent();
});
searchInput.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        return searchEvent();
    }
});


function searchEvent() {
    const searchTerm = searchInput.value.trim();
    if (isSearching){return}
    if (prevTerm === searchTerm){return}
    isSearching = true;
    showLoading();
    getResult(searchTerm);
    prevTerm = searchTerm;
}
function showLoading() {
    searchResults.innerHTML = '';
    loading.style.display = 'block';
}
function hideLoading() {
    loading.style.display = 'none';
}
function getResult(searchTerm) {
    $.ajax({
        url: `/search_query?data=${searchTerm}`,
        type: "POST",
        async: true,
        success: function(response) {
            displayResults(response);
        },
        error: function(xhr, status, error) {
            displayResults(xhr.responseText);
        }
    })
}
function displayResults(response) {
    searchResults.innerHTML = response
    hideLoading();
    isSearching = false;
}
//AjaxPagination
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('page-link')) {
        console.log('click detected')
        if (event.target.parentNode.classList.contains('active')) {return}
        event.preventDefault(); // Prevent the default link behavior
        const page = event.target.getAttribute('data-value');
        if (page && !isSearching) {
            // Perform your pagination logic or AJAX request based on the page clicked
            isSearching = true;
            const pageParam = page.includes('?') ? `&${page.split('?')[1]}` : page;
            const searchTerm = searchInput.value.trim();
            const newTerm = `${searchTerm}${pageParam}`
            showLoading();
            getResult(newTerm);
        }
    }
});