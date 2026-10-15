<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="h3 fw-bold">Executive Overview</h2>
</div>

<div class="row g-3 mb-4">
    <div class="col-md-3">
        <div class="card border-0 shadow-sm bg-primary text-white">
            <div class="card-body">
                <h6 class="text-white-50">Total Contacts</h6>
                <h2 class="display-6 fw-bold mb-0"><?= $total_contacts ?></h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm bg-success text-white">
            <div class="card-body">
                <h6 class="text-white-50">Companies</h6>
                <h2 class="display-6 fw-bold mb-0"><?= $total_companies ?></h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm bg-info text-white">
            <div class="card-body">
                <h6 class="text-white-50">Active Pipeline Value</h6>
                <h2 class="display-6 fw-bold mb-0">$<?= number_format($pipeline_value, 2) ?></h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card border-0 shadow-sm bg-warning text-dark">
            <div class="card-body">
                <h6 class="text-dark-50">Pending Tasks</h6>
                <h2 class="display-6 fw-bold mb-0"><?= $pending_tasks ?></h2>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-md-6">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Sales Stage Metrics</div>
            <div class="card-body">
                <div class="list-group list-group-flush">
                    <?php foreach ($deal_stages as $stage): ?>
                    <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                        <span><i class="bi bi-bar-chart-line text-primary me-2"></i><?= htmlspecialchars($stage['stage']) ?></span>
                        <div>
                            <span class="badge bg-secondary rounded-pill me-2"><?= $stage['count'] ?> deals</span>
                            <span class="fw-bold">$<?= number_format((float)$stage['total_amount'], 2) ?></span>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">Recent Opportunities</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0 align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Title</th>
                                <th>Stage</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($recent_deals as $deal): ?>
                            <tr>
                                <td><?= htmlspecialchars($deal['title']) ?></td>
                                <td><span class="badge bg-primary"><?= htmlspecialchars($deal['stage']) ?></span></td>
                                <td>$<?= number_format((float)$deal['amount'], 2) ?></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>