<?php
declare(strict_types=1);

return [
    'name'     => $_ENV['APP_NAME'] ?? 'ProCRM System',
    'base_url' => $_ENV['APP_URL'] ?? 'http://localhost:8000',
    'roles'    => [
        'admin'   => 'Administrator',
        'manager' => 'Sales Manager',
        'agent'   => 'Sales Agent'
    ],
    'deal_stages' => [
        'New'           => 'New Lead',
        'Qualification' => 'Qualification',
        'Proposal'      => 'Proposal Sent',
        'Negotiation'   => 'In Negotiation',
        'Won'           => 'Closed Won',
        'Lost'          => 'Closed Lost'
    ]
];