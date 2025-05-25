document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById('typeit-text-values');
  
    if (el) {
      // Get raw dataset strings
      const totalJobsRaw = el.dataset.totalJobs;
      const totalOrgsRaw = el.dataset.totalOrgs;
  
      // Convert and format only if both exist and are valid numbers
      if (totalJobsRaw && totalOrgsRaw) {
        const totalJobsNum = Number(totalJobsRaw.trim());
        const totalOrgsNum = Number(totalOrgsRaw.trim());
  
        if (!isNaN(totalJobsNum) && !isNaN(totalOrgsNum)) {
          const totalJobs = totalJobsNum.toLocaleString();
          const totalOrgs = totalOrgsNum.toLocaleString();
  
          new TypeIt("#typeit-text", {
            speed: 75,
            breakLines: false,
            loop: false,
            waitUntilVisible: true
          })
            .type(`${totalJobs} jobs across ${totalOrgs} organizations. `, { delay: 1000 })
            .break()
            .type('No fake jobs. ', { delay: 1000 })
            .type('No <em>middle man.</em>', { delay: 0 })
            .go();
        }
      }
    }
  });
  