# Preface

Django Admin is a mature backend management tool. Register a model, and you get a full create/read/update/delete interface automatically.
But it has a fundamental limitation: it was designed for models, and its boundary ends there.

If you want to add a functional page to the admin that isn't tied to a model, or split different feature modules into independent units that
can be maintained and combined on demand, Django Admin can't help you with that. Not because it falls short — but because it was never
designed for that purpose.

Pinmok does one thing: open up that boundary.

It adds a layer on top of Django Admin, freeing the backend from being model-only. Any feature can be integrated as an application module —
developed independently, installed independently, with menus and permissions automatically registered into the system. Install what you
need, remove what you don't, and modules remain isolated from one another. The whole system is assembled piece by piece. That's where the
name comes from: Pinmok — pin modules.

For developers, working with Pinmok feels almost identical to working with Django Admin. There's no new framework to learn — most developers
are productive within an hour or two. Pinmok follows Django's conventions closely, imposes no version lock-in, and upgrades alongside Django
without friction. Your code stays yours.

Pinmok is open source, MIT licensed, and free to use. Official modules are released on an ongoing basis. Pinmok Content is already
available — a lightweight content management module with template-driven site building and a full API for headless architectures. You can
also build your own modules, contribute them to the community, or keep them private to your own project.

**Suitable for:** enterprise internal management systems, data analytics and monitoring dashboards, IoT device management, crawler task
scheduling, and any Django project that needs an extensible backend.

This documentation is intended for developers with a working knowledge of Django. It walks through the complete flow from installation to
building your first Pinmok application. Each chapter opens with a cheat sheet for quick reference once you're familiar with the material.

## Contributing

Pinmok was founded in April 2025. The author built it entirely in their spare time, and over a year of careful iteration has gone into
refining the architecture and optimizing the internals — with a firm commitment to clean, purposeful code over bloated shortcuts.

Version 1.0 is now officially released, but development is far from over. Long-term iteration and improvement are planned.

The project is still in its early growth stage, with many features and ideas yet to be realized. If this direction resonates with you,
contributions of any kind are welcome. For an independent open source project, every Star on the repository is real, meaningful support.

- GitHub: [github.com/pinmok/pinmok](https://github.com/pinmok/pinmok)
- Gitee: [gitee.com/pinmok/pinmok](https://gitee.com/pinmok/pinmok)