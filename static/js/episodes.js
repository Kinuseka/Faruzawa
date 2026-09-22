document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.nav-link');

    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
            showGroup(index);
        });
    });
});

function showGroup(groupNum) {
    const buttons = document.querySelectorAll('.btn-group .grp-but');
    const contents = document.querySelectorAll('.group-content');

    buttons.forEach(btn => btn.classList.remove('active'));
    contents.forEach(content => content.classList.remove('active'));

    const targetBtn = document.getElementById(`group-${groupNum}-btn`);
    const targetContent = document.getElementById(`group-${groupNum}`);

    targetBtn.classList.add('active');
    targetContent.classList.add('active');
}
function redirectToEpisode(episodeNum) {
    const url = `${window.location}/episode-${episodeNum}`;
    window.location.href = url;
}