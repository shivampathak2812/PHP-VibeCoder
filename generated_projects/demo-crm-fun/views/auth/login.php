<div class="row justify-content-center mt-5">
    <div class="col-md-4">
        <div class="card shadow-sm border-0">
            <div class="card-body p-4">
                <div class="text-center mb-4">
                    <h3 class="fw-bold text-primary"><i class="bi bi-diagram-3-fill me-1"></i> ProCRM</h3>
                    <p class="text-muted">Sign in to your CRM workspace</p>
                </div>
                
                <?php if (!empty($error)): ?>
                    <div class="alert alert-danger py-2 small"><?= htmlspecialchars($error) ?></div>
                <?php endif; ?>

                <form method="POST" action="index.php?route=login">
                    <?= \Core\Csrf::field() ?>
                    <div class="mb-3">
                        <label class="form-label">Email Address</label>
                        <input type="email" name="email" class="form-control" placeholder="admin@example.com" required autofocus>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control" placeholder="••••••••" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 py-2">Log In</button>
                </form>
            </div>
        </div>
    </div>
</div>