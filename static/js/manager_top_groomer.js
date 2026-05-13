// This JS file handles fetching and rendering the Top Performer Groomer section on the manager dashboard

document.addEventListener('DOMContentLoaded', function() {
    const topGroomerSection = document.getElementById('top-groomer-section');
    const periodSelect = document.getElementById('top-groomer-period');
    const resultContainer = document.getElementById('top-groomer-result');

    function fetchTopGroomers() {
        const periodType = periodSelect.value;
        let url = `/accounts/api/top-groomer/?period_type=${periodType}`;
        // For custom range, you can add date_from and date_to params
        fetch(url)
            .then(res => res.json())
            .then(data => {
                renderTopGroomers(data);
            })
            .catch(() => {
                resultContainer.innerHTML = '<div class="text-red-500">Gagal memuat data.</div>';
            });
    }

    function renderTopGroomers(data) {
        if (!data || !data.length) {
            resultContainer.innerHTML = '<div class="text-gray-500 text-center py-6">Belum ada data groomer dengan booking selesai pada periode ini.</div>';
            return;
        }
        let html = '<div class="space-y-3">';
        data.forEach((groomer, idx) => {
            html += `<div class="flex items-center justify-between p-3 bg-teal-50 rounded-xl border border-teal-100">
                <div class="flex items-center gap-3">
                    <span class="text-2xl font-bold text-teal-600">${groomer.rank}</span>
                    <span class="font-semibold text-gray-800">${groomer.groomer_name}</span>
                </div>
                <span class="font-bold text-gray-900">${groomer.completed_count} Booking</span>
            </div>`;
        });
        html += '</div>';
        resultContainer.innerHTML = html;
    }

    if (topGroomerSection && periodSelect) {
        periodSelect.addEventListener('change', fetchTopGroomers);
        fetchTopGroomers();
    }
});
