Importing Your Documentation
=============================
To import a public documentation repository, visit your `Read the Docs dashboard <https://readthedocs.org/dashboard>`_ and click Import. For private repositories, please use `Read the Docs for Business <https://docs.readthedocs.io/en/stable/commercial/index.html>`_

If you have `connected your Read the Docs account <https://docs.readthedocs.io/en/stable/connected-accounts.html>`_ to GitHub, Bitbucket, or GitLab, you will see a list of your repositories that we are able to import. To import one of these projects, just click the import icon next to the repository you’d like to import. This will bring up a form that is already filled with your project’s information. Feel free to edit any of these properties, and then click Next to :ref:`build your documentation </IMPORTDOC:Building your documentation>`.

Manually import your docs
---------------------------
If you do not have a connected account, you will need to select Import Manually and enter the information for your repository yourself. You will also need to manually configure the webhook for your repository as well. When importing your project, you will be asked for the repository URL, along with some other information for your new project. The URL is normally the URL or path name you'd use to checkout, clone, or branch your repository. Some examples:

Git: https://github.com/ericholscher/django-kong.git
Mercurial: https://bitbucket.org/ianb/pip
Subversion: http://varnish-cache.org/svn/trunk
Bazaar: lp:pasta
Add an optional homepage URL and some tags, and then click Next.

Once your project is created, you'll need to manually configure the repository webhook if you would like to have new changes trigger builds for your project on Read the Docs. Go to your project's :guilabel:`Admin` > :guilabel:`Integrations` page to configure a new webhook, or see `our steps for webhook creation <https://docs.readthedocs.io/en/stable/webhooks.html#webhook-creation>`_ for more information on this process.

Note

The Admin page can be found at https://readthedocs.org/dashboard/<project-slug>/edit/. You can access all of the project settings from the admin page sidebar.
