document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById('typeit-text-values');

    if (el){

        const totalJobs = el.dataset.totalJobs?.trim().toLocaleString();
        const totalOrgs = el.dataset.totalOrgs?.trim().toLocaleString();

        if (totalJobs && !isNaN(Number(totalJobs)) &&
            totalOrgs && !isNaN(Number(totalOrgs)))
        {
            
            new TypeIt("#typeit-text", {
                speed: 75,
                breakLines: true,
                loop: false,
                waitUntilVisible: true,
                afterComplete: function (instance) {
                    instance.destroy();
                }
            })
            .type(`${totalJobs} jobs across ${totalOrgs} organizations. `, { delay: 1000 })
            .break()
            .type('No fake jobs. No <em>middle man.</em>', {delay:0})
            .go();

        }
    }
});
