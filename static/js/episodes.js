function showGroup(groupNum) {
    const buttons = document.querySelectorAll('.episode-range-scroll .grp-but');
    const contents = document.querySelectorAll('.group-content');

    buttons.forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
    });
    contents.forEach(content => content.classList.remove('active'));

    const targetBtn = document.getElementById(`group-${groupNum}-btn`);
    const targetContent = document.getElementById(`group-${groupNum}`);

    if (targetBtn) {
        targetBtn.classList.add('active');
        targetBtn.setAttribute('aria-selected', 'true');
    }
    if (targetContent) {
        targetContent.classList.add('active');
    }
}

function redirectToEpisode(episodeNum) {
    const url = `${window.location}/episode-${episodeNum}`;
    window.location.href = url;
}
