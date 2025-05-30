document.addEventListener('DOMContentLoaded', () => {
  const typeitText = document.getElementById('typeit-text');
  const valuesEl = document.getElementById('typeit-text-values');

  if (typeitText && valuesEl) {
    const totalJobsRaw = valuesEl.dataset.totalJobs;
    const totalOrgsRaw = valuesEl.dataset.totalOrgs;

    const totalJobsNum = Number(totalJobsRaw?.trim());
    const totalOrgsNum = Number(totalOrgsRaw?.trim());

    if (!isNaN(totalJobsNum) && !isNaN(totalOrgsNum)) {
      const totalJobs = totalJobsNum.toLocaleString();
      const totalOrgs = totalOrgsNum.toLocaleString();

      new TypeIt("#typeit-text", {
        speed: 75,
        breakLines: false,
        loop: false,
        waitUntilVisible: false
      })
        .type(`${totalJobs} jobs across ${totalOrgs} organizations. `, { delay: 1000 })
        .break()
        .type('No fake jobs. ', { delay: 1000 })
        .type('No <em>middle man.</em>', { delay: 0 })
        .go();
    }
  }
});
