import subprocess
import re
from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open,logger

def _remove_comments (text_line,comment="#"):
    literal_comment = "LITERALCOMMENT"
    text_line = text_line.replace("\{}".format(comment),literal_comment)
    text_line = text_line.split(comment)[0].strip()
    return text_line.replace(literal_comment,comment)

def extra_meta (\
    text_lines,
    meta_regx="^([A-Za-z0-9_.]*) *:",
    line_break="+",
    meta_end="\n",
    comment="#"):
    """ Take lines of text and extract the meta information from it 

    Parameters 
    text_lines : list of strings 
    meta_regx : string 
        Regular expression to find the meta names 
    comment : string 
        string character representing comments 

    Returns 
    context : string 
    meta : dict 

    """
    content = ""
    meta = {}
    name = ""
    for i, line in enumerate(text_lines):
        # search the line for the regular expression
        s = re.search(meta_regx,line)
        # if you find a blank line then the rest is content        
        if s is None and not len(line.rstrip()):
            content = "\n".join(text_lines[i:])
            break
        # forced line breaks in metadata
        if line.rstrip() == line_break:
            line = "\n"
        # else if you find a new keyword
        if s is not None:
            if len(name):
                meta[name] = values 
            name = s.groups()[0].lower()
            values = [_remove_comments(line[len(name)+1:])]
        # else if there is already a keyword
        elif len(name):
            values.append(_remove_comments(line))
    if len(name):
        meta[name] = values 
    return content,meta

class PandocReader(BaseReader):
    enabled = True
    file_extensions = ['md', 'markdown', 'mkd', 'mdown']

    meta_regx = "^([A-Za-z0-9_.]*) *:"
    comment = "#"
    meta_line_break = "+"
    
    def _extract_metadata (self,text_lines):

        content,meta = extra_meta(\
            text_lines,
            meta_regx=self.meta_regx,
            line_break=self.meta_line_break,
            comment=self.comment,
            )

        metadata = {}
        for name in meta:
            values = meta[name]
            if len(values) == 0:
                metadata[name] = self.process_metadata(name,"")
                continue
            if name == "summary":
                val = self._convert_markdown("\n".join(values))
                metadata[name] = self.process_metadata(name,val)
            elif len(values) == 1:
                metadata[name] = self.process_metadata(name,values[0].strip())
            else:
                metadata[name] = self.process_metadata(name,values)

        return content, metadata

    def _convert_markdown (self,content):
        extra_args = self.settings.get('PANDOC_ARGS', [])
        extensions = self.settings.get('PANDOC_EXTENSIONS', '')
        if isinstance(extensions, list):
            extensions = ''.join(extensions)

        pandoc_cmd = ["pandoc", "--from=markdown" + extensions, "--to=html5"]
        pandoc_cmd.extend(extra_args)

        logger.debug("pandoc_reader: execute `{}`".format(" ".join(pandoc_cmd)))

        proc = subprocess.Popen(pandoc_cmd,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE)

        output = proc.communicate(content.encode('utf-8'))[0].decode('utf-8')
        status = proc.wait()
        if status:   
            logger.error(proc.stdout.read())
            raise subprocess.CalledProcessError(status, pandoc_cmd)

        return output 

    def read(self, filename):
        logger.debug("pandoc_reader: reading '{}'".format(filename))
        with pelican_open(filename) as fp:
            text = list(fp.splitlines())
        content,metadata = self._extract_metadata(text)
        output = self._convert_markdown(content)
        return output, metadata

def add_reader(readers):
    for ext in PandocReader.file_extensions:
        readers.reader_classes[ext] = PandocReader

def register():
    signals.readers_init.connect(add_reader)
