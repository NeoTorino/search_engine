document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById('typeit-text');
    const totalJobs = Number(el.dataset.totalJobs).toLocaleString();
    const totalOrgs = Number(el.dataset.totalOrgs).toLocaleString();

    new TypeIt("#typeit-text", {
        speed: 75,
        breakLines: false,
        loop: true,
        waitUntilVisible: true,
    })
        .type(`${totalJobs} jobs.`)
        .pause(1500)
        .delete(null, { delay: 500 })
        .type(`${totalOrgs} organizations.`)
        .pause(1500)
        .delete(null, { delay: 500 })
        .type(["No more fake jobs."])
        .pause(1500)
        .delete(null, { delay: 500 })
        .go();
});
